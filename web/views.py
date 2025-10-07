from __future__ import annotations
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from datetime import date, datetime
from sqlalchemy import func, select
from sqlalchemy.orm import Session
import json

from app.db_sa import get_session
from app.models_sa import LoanORM, InstallmentORM

bp = Blueprint("views", __name__)


@bp.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@bp.route("/")
def index():
    q = (request.args.get("q", "") or "").strip().lower()
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
        # Debug info
        print(f"DEBUG: urgent_count={urgent_count}, total_count={len(loans)}, total_remaining={total_remaining}")
        return render_template("index.html", items=enriched, q=q, urgent_count=urgent_count, total_count=len(loans), total_remaining=total_remaining)


@bp.route("/loan/new", methods=["GET", "POST"])
@bp.route("/loan/<int:loan_id>", methods=["GET", "POST"])
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
def delete_loan_route(loan_id: int):
    with get_session() as session:
        loan = session.get(LoanORM, loan_id)
        if loan:
            session.delete(loan)
    flash("Кредит удален", "success")
    return redirect(url_for("views.index"))


@bp.route("/export/json")
def export_json():
    """Экспорт всех данных в JSON файл для скачивания через браузер."""
    try:
        with get_session() as session:
            # Получаем все кредиты
            loans = session.execute(select(LoanORM)).scalars().all()
            
            loans_data = []
            for loan in loans:
                loan_dict = {
                    'id': loan.id,
                    'website': loan.website,
                    'loan_date': loan.loan_date,
                    'amount_borrowed': float(loan.amount_borrowed),
                    'amount_due': float(loan.amount_due),
                    'due_date': loan.due_date,
                    'risky_org': bool(loan.risky_org),
                    'notes': loan.notes,
                    'payment_methods': loan.payment_methods,
                    'reminded_pre_due': bool(loan.reminded_pre_due),
                    'created_at': loan.created_at,
                    'is_paid': bool(loan.is_paid),
                    'org_name': loan.org_name
                }
                loans_data.append(loan_dict)
            
            # Получаем все рассрочки
            installments = session.execute(select(InstallmentORM)).scalars().all()
            
            installments_data = []
            for installment in installments:
                installment_dict = {
                    'id': installment.id,
                    'loan_id': installment.loan_id,
                    'due_date': installment.due_date,
                    'amount': float(installment.amount),
                    'paid': bool(installment.paid),
                    'paid_date': installment.paid_date,
                    'created_at': installment.created_at
                }
                installments_data.append(installment_dict)
            
            # Создаем структуру данных для экспорта
            export_data = {
                'export_info': {
                    'export_date': datetime.now().isoformat(),
                    'total_loans': len(loans_data),
                    'total_installments': len(installments_data),
                    'exported_by': 'web_interface'
                },
                'loans': loans_data,
                'installments': installments_data
            }
            
            # Создаем имя файла с временной меткой
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"mikrokredit_export_{timestamp}.json"
            
            # Создаем JSON строку
            json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
            
            # Возвращаем файл для скачивания
            return Response(
                json_str,
                mimetype='application/json',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Type': 'application/json; charset=utf-8'
                }
            )
            
    except Exception as e:
        flash(f"Ошибка при экспорте данных: {str(e)}", "error")
        return redirect(url_for("views.index"))
