from __future__ import annotations
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from datetime import date, datetime
from sqlalchemy import func, select
from sqlalchemy.orm import Session
import json

from app.integration import cache_manager, api_gateway_client
from app.auth import login_required
from app.db_sa import get_session
from app.models_sa import LoanORM, InstallmentORM, TaskORM

bp = Blueprint("views", __name__)


@bp.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@bp.route("/")
@login_required
def dashboard():
    """Главная страница - Dashboard"""
    with get_session() as session:
        # Используем ТУ ЖЕ логику что и в разделе займов
        loans = session.execute(select(LoanORM)).scalars().all()
        today = date.today()
        total_remaining = 0.0
        urgent_count = 0
        urgent_loans = []
        
        for l in loans:
            # Вычисляем сумму неоплаченных платежей из installments
            unpaid_total = session.execute(
                select(func.coalesce(func.sum(InstallmentORM.amount), 0.0)).where(
                    InstallmentORM.loan_id == l.id, InstallmentORM.paid == 0
                )
            ).scalar_one()
            
            # Определяем оплачен ли займ (по installments)
            derived_paid = unpaid_total == 0
            
            # Находим ближайший неоплаченный платёж
            next_row = None if derived_paid else session.execute(
                select(InstallmentORM).where(InstallmentORM.loan_id == l.id, InstallmentORM.paid == 0)
                .order_by(InstallmentORM.due_date.asc(), InstallmentORM.id.asc())
                .limit(1)
            ).scalar_one_or_none()
            
            next_date = (next_row.due_date if next_row else None)
            
            # Вычисляем дни до следующего платежа
            try:
                days_left = None if next_date is None else (date.fromisoformat(next_date) - today).days
            except Exception:
                days_left = None
            
            # Критерий "горящий" - как в оригинале
            urgent = (days_left is not None) and (days_left < 5)
            
            # Суммируем общий долг
            if not derived_paid:
                total_remaining += float(unpaid_total or 0.0)
            
            # Считаем горящие
            if urgent and not derived_paid:
                urgent_count += 1
                urgent_loans.append({
                    'id': l.id,
                    'org_name': l.org_name,
                    'amount_due': unpaid_total,
                    'next_date': next_date,
                    'days_left': days_left
                })
        
        # Статистика по займам (как в оригинале)
        loans_stats = {
            'total': len(loans),
            'unpaid': sum(1 for l in loans if session.execute(
                select(func.coalesce(func.sum(InstallmentORM.amount), 0.0)).where(
                    InstallmentORM.loan_id == l.id, InstallmentORM.paid == 0
                )
            ).scalar_one() > 0),
            'total_debt': total_remaining,
            'urgent_count': urgent_count
        }
        
        # Сортируем горящие по дням
        urgent_loans.sort(key=lambda x: x['days_left'])
        
        # Статистика по задачам
        tasks_stats = {
            'total': session.execute(select(func.count(TaskORM.id))).scalar() or 0,
            'pending': session.execute(select(func.count(TaskORM.id)).where(TaskORM.status == 0)).scalar() or 0,
            'today': session.execute(
                select(func.count(TaskORM.id))
                .where(
                    TaskORM.due_date.like(f'{today.isoformat()}%'),
                    TaskORM.status == 0
                )
            ).scalar() or 0,
            'overdue': session.execute(
                select(func.count(TaskORM.id))
                .where(
                    TaskORM.due_date < datetime.now().isoformat(),
                    TaskORM.status == 0
                )
            ).scalar() or 0
        }
        
        # Задачи на сегодня
        today_tasks = session.execute(
            select(TaskORM)
            .where(
                TaskORM.due_date.like(f'{today.isoformat()}%'),
                TaskORM.status == 0
            )
            .order_by(TaskORM.importance.asc())
            .limit(5)
        ).scalars().all()
        
        today_tasks_data = [
            {
                'id': t.id,
                'title': t.title,
                'importance': t.importance,
                'due_date': t.due_date
            }
            for t in today_tasks
        ]
        
    return render_template(
        'dashboard.html',
        loans_stats=loans_stats,
        urgent_loans=urgent_loans,
        tasks_stats=tasks_stats,
        today_tasks=today_tasks_data
    )


@bp.route("/loans")
@login_required
def loans_index():
    q = (request.args.get("q", "") or "").strip().lower()
    
    # Try to get cached data first
    cache_key = f"loans_data_{hash(q)}"
    cached_data = cache_manager.get_cached_loans_data()
    
    if cached_data and not q:  # Use cache only for main page without search
        return render_template("index.html", **cached_data)
    
    with get_session() as session:
        loans = session.execute(select(LoanORM)).scalars().all()
        if q:
            loans = [l for l in loans if q in (l.org_name or "").lower() or q in (l.website or "").lower() or q in (l.notes or "").lower()]
        enriched = []
        today = date.today()
        total_remaining = 0.0
        urgent_count = 0
        for l in loans:
            unpaid_total = session.execute(
                select(func.coalesce(func.sum(InstallmentORM.amount), 0.0)).where(
                    InstallmentORM.loan_id == l.id, InstallmentORM.paid == 0
                )
            ).scalar_one()
            derived_paid = unpaid_total == 0
            next_row = None if derived_paid else session.execute(
                select(InstallmentORM).where(InstallmentORM.loan_id == l.id, InstallmentORM.paid == 0)
                .order_by(InstallmentORM.due_date.asc(), InstallmentORM.id.asc())
                .limit(1)
            ).scalar_one_or_none()
            last_date = session.execute(
                select(func.max(InstallmentORM.due_date)).where(InstallmentORM.loan_id == l.id)
            ).scalar_one()
            total_due = session.execute(
                select(func.coalesce(func.sum(InstallmentORM.amount), 0.0)).where(InstallmentORM.loan_id == l.id)
            ).scalar_one()
            next_date = (next_row.due_date if next_row else None)
            try:
                days_left = None if next_date is None else (date.fromisoformat(next_date) - today).days
            except Exception:
                days_left = None
            urgent = (days_left is not None) and (days_left < 5)
            if not derived_paid:
                total_remaining += float(unpaid_total or 0.0)
            if urgent and not derived_paid:
                urgent_count += 1
            enriched.append({
                "loan": l,
                "next_date": next_date,
                "next_amount": (next_row.amount if next_row else None),
                "remaining": float(unpaid_total or 0.0),
                "last_date": last_date,
                "paid": derived_paid,
                "urgent": urgent,
            })
        enriched.sort(key=lambda x: ("9999-12-31" if x["next_date"] is None else x["next_date"], x["loan"].id or 0))
        
        # Cache the result if no search query
        if not q:
            cache_data = {
                "items": enriched,
                "q": q,
                "urgent_count": urgent_count,
                "total_count": len(loans),
                "total_remaining": total_remaining
            }
            cache_manager.cache_loans_data(cache_data)
        
        # Debug info
        print(f"DEBUG: urgent_count={urgent_count}, total_count={len(loans)}, total_remaining={total_remaining}")
        return render_template("index.html", items=enriched, q=q, urgent_count=urgent_count, total_count=len(loans), total_remaining=total_remaining)


@bp.route("/loan/new", methods=["GET", "POST"])
@login_required
def loan_new():
    return loan_edit(None)

@bp.route("/loan/<int:loan_id>", methods=["GET", "POST"])
@login_required
def loan_edit(loan_id: int | None = None):
    if request.method == "POST":
        try:
            org_name = request.form.get("org_name", "").strip()
            website = request.form.get("website", "").strip()
            loan_date = request.form.get("loan_date", "")
            due_date = request.form.get("due_date", "")
            amount_borrowed = float(request.form.get("amount_borrowed", 0) or 0)
            notes = request.form.get("notes", "")
            payment_methods = request.form.get("payment_methods", "")
            risky_org = 1 if request.form.get("risky_org") == "on" else 0
            
            print(f"DEBUG: Creating loan - org_name={org_name}, website={website}, loan_date={loan_date}, due_date={due_date}")
            
            if not org_name or not website:
                flash("Укажите название организации и сайт", "error")
                return redirect(request.url)
            if due_date < loan_date:
                flash("Дата возврата не может быть раньше даты оформления", "error")
                return redirect(request.url)
            
            with get_session() as session:
                if loan_id is None:
                    loan = LoanORM(
                        website=website,
                        loan_date=loan_date,
                        amount_borrowed=amount_borrowed,
                        amount_due=0.0,
                        due_date=due_date,
                        risky_org=int(risky_org),
                        notes=notes,
                        payment_methods=payment_methods,
                        reminded_pre_due=0,
                        created_at=date.today().isoformat(),
                        is_paid=0,
                        org_name=org_name,
                    )
                    session.add(loan)
                    session.commit()
                    loan_id = loan.id
                    print(f"DEBUG: Created loan with ID {loan_id}")
                    
                    # Clear cache after data change
                    cache_manager.delete("loans_data")
                    
                    flash("Кредит создан", "success")
                else:
                    loan = session.get(LoanORM, loan_id)
                    if loan is None:
                        flash("Кредит не найден", "error")
                        return redirect(url_for("views.index"))
                    loan.website = website
                    loan.loan_date = loan_date
                    loan.amount_borrowed = amount_borrowed
                    loan.due_date = due_date
                    loan.risky_org = int(risky_org)
                    loan.notes = notes
                    loan.payment_methods = payment_methods
                    loan.org_name = org_name
                    flash("Сохранено", "success")
            
            print(f"DEBUG: Redirecting to loan_edit with loan_id={loan_id}")
            return redirect(url_for("views.loan_edit", loan_id=loan_id))
            
        except Exception as e:
            print(f"ERROR in loan_edit POST: {e}")
            flash(f"Ошибка при сохранении: {str(e)}", "error")
            return redirect(request.url)

    # GET
    try:
        with get_session() as session:
            loan = session.get(LoanORM, loan_id) if loan_id is not None else None
            insts = []
            remaining = 0.0
            total_due = 0.0
            last_date = None
            if loan is not None:
                insts = session.execute(
                    select(InstallmentORM).where(InstallmentORM.loan_id == loan.id).order_by(
                        InstallmentORM.due_date.asc(), InstallmentORM.id.asc()
                    )
                ).scalars().all()
                remaining = session.execute(
                    select(func.coalesce(func.sum(InstallmentORM.amount), 0.0)).where(
                        InstallmentORM.loan_id == loan.id, InstallmentORM.paid == 0
                    )
                ).scalar_one()
                total_due = session.execute(
                    select(func.coalesce(func.sum(InstallmentORM.amount), 0.0)).where(InstallmentORM.loan_id == loan.id)
                ).scalar_one()
                last_date = session.execute(
                    select(func.max(InstallmentORM.due_date)).where(InstallmentORM.loan_id == loan.id)
                ).scalar_one()
            return render_template("loan_edit.html", loan=loan, installments=insts, remaining=remaining, total_due=total_due, last_date=last_date)
    except Exception as e:
        print(f"ERROR in loan_edit GET: {e}")
        flash(f"Ошибка при загрузке: {str(e)}", "error")
        return redirect(url_for("views.index"))


@bp.post("/loan/<int:loan_id>/installments/add")
@login_required
def add_inst(loan_id: int):
    due_date = request.form.get("due_date", "")
    amount = float(request.form.get("amount", 0) or 0)
    if amount <= 0:
        flash("Сумма должна быть больше нуля", "error")
        return redirect(url_for("views.loan_edit", loan_id=loan_id))
    with get_session() as session:
        loan = session.get(LoanORM, loan_id)
        if loan is None:
            flash("Кредит не найден", "error")
            return redirect(url_for("views.index"))
        inst = InstallmentORM(
            loan_id=loan_id, due_date=due_date, amount=amount, paid=0, paid_date=None, created_at=date.today().isoformat()
        )
        session.add(inst)
        # Recalc derived fields
        total = session.execute(
            select(func.coalesce(func.sum(InstallmentORM.amount), 0.0)).where(InstallmentORM.loan_id == loan_id)
        ).scalar_one()
        unpaid = session.execute(
            select(func.coalesce(func.sum(InstallmentORM.amount), 0.0)).where(InstallmentORM.loan_id == loan_id, InstallmentORM.paid == 0)
        ).scalar_one()
        loan.amount_due = float(total or 0.0)
        loan.is_paid = 1 if (unpaid or 0.0) == 0.0 else 0
    flash("Платеж добавлен", "success")
    return redirect(url_for("views.loan_edit", loan_id=loan_id))


@bp.post("/loan/<int:loan_id>/installments/<int:inst_id>/edit")
@login_required
def edit_inst(loan_id: int, inst_id: int):
    due_date = request.form.get("due_date", "")
    amount = float(request.form.get("amount", 0) or 0)
    if amount <= 0:
        flash("Сумма должна быть больше нуля", "error")
        return redirect(url_for("views.loan_edit", loan_id=loan_id))
    with get_session() as session:
        loan = session.get(LoanORM, loan_id)
        if loan is None:
            flash("Кредит не найден", "error")
            return redirect(url_for("views.index"))
        inst = session.get(InstallmentORM, inst_id)
        if inst is None or inst.loan_id != loan_id:
            flash("Платеж не найден", "error")
            return redirect(url_for("views.loan_edit", loan_id=loan_id))
        inst.due_date = due_date
        inst.amount = amount
        # Recalc derived fields
        total = session.execute(
            select(func.coalesce(func.sum(InstallmentORM.amount), 0.0)).where(InstallmentORM.loan_id == loan_id)
        ).scalar_one()
        unpaid = session.execute(
            select(func.coalesce(func.sum(InstallmentORM.amount), 0.0)).where(InstallmentORM.loan_id == loan_id, InstallmentORM.paid == 0)
        ).scalar_one()
        loan.amount_due = float(total or 0.0)
        loan.is_paid = 1 if (unpaid or 0.0) == 0.0 else 0
    flash("Платеж изменен", "success")
    return redirect(url_for("views.loan_edit", loan_id=loan_id))

@bp.post("/loan/<int:loan_id>/installments/<int:inst_id>/toggle")
@login_required
def toggle_inst(loan_id: int, inst_id: int):
    action = request.form.get("action", "toggle")
    with get_session() as session:
        loan = session.get(LoanORM, loan_id)
        if loan is None:
            flash("Кредит не найден", "error")
            return redirect(url_for("views.index"))
        if action == "delete":
            inst = session.get(InstallmentORM, inst_id)
            if inst:
                session.delete(inst)
            flash("Платеж удален", "success")
        else:
            new_paid = request.form.get("paid") == "1"
            inst = session.get(InstallmentORM, inst_id)
            if inst is None:
                flash("Платеж не найден", "error")
                return redirect(url_for("views.loan_edit", loan_id=loan_id))
            inst.paid = 1 if new_paid else 0
            inst.paid_date = date.today().isoformat() if new_paid else None
            flash("Статус платежа обновлен", "success")
        # Recalc derived fields
        total = session.execute(
            select(func.coalesce(func.sum(InstallmentORM.amount), 0.0)).where(InstallmentORM.loan_id == loan_id)
        ).scalar_one()
        unpaid = session.execute(
            select(func.coalesce(func.sum(InstallmentORM.amount), 0.0)).where(InstallmentORM.loan_id == loan_id, InstallmentORM.paid == 0)
        ).scalar_one()
        loan.amount_due = float(total or 0.0)
        loan.is_paid = 1 if (unpaid or 0.0) == 0.0 else 0
    return redirect(url_for("views.loan_edit", loan_id=loan_id))


@bp.post("/loan/<int:loan_id>/delete")
@login_required
def delete_loan_route(loan_id: int):
    # JSON API
    if request.is_json:
        try:
            with get_session() as session:
                loan = session.get(LoanORM, loan_id)
                if loan is None:
                    return jsonify({"success": False, "error": "Займ не найден"}), 404
                session.delete(loan)
                session.commit()
                cache_manager.delete("loans_data")
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    # HTML form
    with get_session() as session:
        loan = session.get(LoanORM, loan_id)
        if loan:
            session.delete(loan)
            session.commit()
            cache_manager.delete("loans_data")
    flash("Кредит удален", "success")
    return redirect(url_for("views.loans_index"))


# ========== НОВЫЕ МАРШРУТЫ V2 ==========

@bp.route("/loan/new/v2", methods=["GET"])
@login_required
def loan_new_v2():
    """Новый интерфейс создания займа"""
    return render_template("loan_edit_v2.html", 
                         loan_json="null", 
                         installments_json="[]",
                         is_edit=False)


@bp.route("/loan/<int:loan_id>/v2", methods=["GET"])
@login_required
def loan_edit_v2(loan_id: int):
    """Новый интерфейс редактирования займа"""
    with get_session() as session:
        loan_orm = session.get(LoanORM, loan_id)
        if loan_orm is None:
            flash("Займ не найден", "error")
            return redirect(url_for("views.loans_index"))
        
        # Извлекаем данные в словарь
        loan_json = json.dumps({
            'id': loan_orm.id,
            'org_name': loan_orm.org_name or '',
            'website': loan_orm.website or '',
            'loan_date': loan_orm.loan_date or '',
            'amount_borrowed': float(loan_orm.amount_borrowed or 0),
            'amount_due': float(loan_orm.amount_due or 0),
            'due_date': loan_orm.due_date or '',
            'risky_org': bool(loan_orm.risky_org),
            'notes': loan_orm.notes or '',
            'payment_methods': loan_orm.payment_methods or '',
            'loan_type': loan_orm.loan_type or 'single',
            'category': loan_orm.category or 'microloan',
            'interest_rate': float(loan_orm.interest_rate or 0)
        })
        
        # Получаем installments
        insts = session.execute(
            select(InstallmentORM)
            .where(InstallmentORM.loan_id == loan_orm.id)
            .order_by(InstallmentORM.due_date.asc())
        ).scalars().all()
        
        # Преобразуем в JSON
        installments_json = json.dumps([{
            'id': inst.id,
            'due_date': inst.due_date,
            'amount': float(inst.amount),
            'paid': bool(inst.paid),
            'paid_date': inst.paid_date
        } for inst in insts])
        
    return render_template("loan_edit_v2.html", 
                         loan_json=loan_json, 
                         installments_json=installments_json,
                         is_edit=True)


@bp.route("/loan/new/save", methods=["POST"])
@login_required
def loan_save_new():
    """Сохранение нового займа (JSON API)"""
    try:
        data = request.get_json()
        
        with get_session() as session:
            # Создаём займ
            loan = LoanORM(
                org_name=data['org_name'],
                website=data['website'],
                loan_date=data['loan_date'],
                amount_borrowed=float(data['amount_borrowed']),
                amount_due=float(data['amount_due']),
                due_date=data['due_date'],
                risky_org=1 if data.get('risky_org') else 0,
                notes=data.get('notes', ''),
                payment_methods=data.get('payment_methods', ''),
                reminded_pre_due=0,
                created_at=datetime.now().isoformat(),
                is_paid=0,
                loan_type=data.get('loan_type', 'single'),
                category=data.get('category', 'microloan'),
                interest_rate=float(data.get('interest_rate', 0))
            )
            session.add(loan)
            session.flush()  # Получаем ID
            
            # Создаём installments если есть
            if data.get('installments'):
                for inst_data in data['installments']:
                    inst = InstallmentORM(
                        loan_id=loan.id,
                        due_date=inst_data['due_date'],
                        amount=float(inst_data['amount']),
                        paid=1 if inst_data.get('paid') else 0,
                        paid_date=inst_data.get('paid_date'),
                        created_at=datetime.now().isoformat()
                    )
                    session.add(inst)
            
            # Синхронизируем is_paid
            sync_loan_paid_status(session, loan.id)
            
            session.commit()
            cache_manager.delete("loans_data")
            
            return jsonify({"success": True, "loan_id": loan.id})
    
    except Exception as e:
        print(f"ERROR in loan_save_new: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/loan/<int:loan_id>/save", methods=["POST"])
@login_required
def loan_save_existing(loan_id: int):
    """Обновление существующего займа (JSON API)"""
    try:
        data = request.get_json()
        
        with get_session() as session:
            loan = session.get(LoanORM, loan_id)
            if loan is None:
                return jsonify({"success": False, "error": "Займ не найден"}), 404
            
            # Обновляем поля займа
            loan.org_name = data['org_name']
            loan.website = data['website']
            loan.loan_date = data['loan_date']
            loan.amount_borrowed = float(data['amount_borrowed'])
            loan.amount_due = float(data['amount_due'])
            loan.due_date = data['due_date']
            loan.risky_org = 1 if data.get('risky_org') else 0
            loan.notes = data.get('notes', '')
            loan.payment_methods = data.get('payment_methods', '')
            loan.loan_type = data.get('loan_type', 'single')
            loan.category = data.get('category', 'microloan')
            loan.interest_rate = float(data.get('interest_rate', 0))
            
            # Удаляем все старые installments
            session.execute(
                select(InstallmentORM).where(InstallmentORM.loan_id == loan_id)
            )
            for inst in session.execute(
                select(InstallmentORM).where(InstallmentORM.loan_id == loan_id)
            ).scalars().all():
                session.delete(inst)
            
            # Создаём новые installments
            if data.get('installments'):
                for inst_data in data['installments']:
                    inst = InstallmentORM(
                        loan_id=loan.id,
                        due_date=inst_data['due_date'],
                        amount=float(inst_data['amount']),
                        paid=1 if inst_data.get('paid') else 0,
                        paid_date=inst_data.get('paid_date'),
                        created_at=datetime.now().isoformat()
                    )
                    session.add(inst)
            
            # Синхронизируем is_paid
            sync_loan_paid_status(session, loan.id)
            
            session.commit()
            cache_manager.delete("loans_data")
            
            return jsonify({"success": True})
    
    except Exception as e:
        print(f"ERROR in loan_save_existing: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def sync_loan_paid_status(session: Session, loan_id: int):
    """Автоматическая синхронизация is_paid на основе installments"""
    loan = session.get(LoanORM, loan_id)
    if loan is None:
        return
    
    # Проверяем есть ли installments
    total_count = session.execute(
        select(func.count(InstallmentORM.id))
        .where(InstallmentORM.loan_id == loan_id)
    ).scalar()
    
    if total_count > 0:
        # Есть installments - проверяем неоплаченные
        unpaid_count = session.execute(
            select(func.count(InstallmentORM.id))
            .where(InstallmentORM.loan_id == loan_id, InstallmentORM.paid == 0)
        ).scalar()
        
        loan.is_paid = 1 if unpaid_count == 0 else 0
    # Если нет installments - оставляем is_paid как есть
