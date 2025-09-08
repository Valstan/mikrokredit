from __future__ import annotations
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import date
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db_sa import get_session
from app.models_sa import LoanORM, InstallmentORM

bp = Blueprint("views", __name__)


@bp.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@bp.route("/")
def index():
    with next(get_session()) as session:  # type: Session
        loans = session.execute(select(LoanORM)).scalars().all()
        enriched = []
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
            enriched.append({
                "loan": l,
                "next_date": (next_row.due_date if next_row else None),
                "next_amount": (next_row.amount if next_row else None),
                "remaining": float(unpaid_total or 0.0),
                "last_date": last_date,
                "paid": derived_paid,
            })
        enriched.sort(key=lambda x: ("9999-12-31" if x["next_date"] is None else x["next_date"], x["loan"].id or 0))
        return render_template("index.html", items=enriched)


@bp.route("/loan/new", methods=["GET", "POST"])
@bp.route("/loan/<int:loan_id>", methods=["GET", "POST"])
def loan_edit(loan_id: int | None = None):
    if request.method == "POST":
        org_name = request.form.get("org_name", "").strip()
        website = request.form.get("website", "").strip()
        loan_date = request.form.get("loan_date", "")
        due_date = request.form.get("due_date", "")
        amount_borrowed = float(request.form.get("amount_borrowed", 0) or 0)
        notes = request.form.get("notes", "")
        payment_methods = request.form.get("payment_methods", "")
        risky_org = 1 if request.form.get("risky_org") == "on" else 0
        if not org_name or not website:
            flash("Укажите название организации и сайт", "error")
            return redirect(request.url)
        if due_date < loan_date:
            flash("Дата возврата не может быть раньше даты оформления", "error")
            return redirect(request.url)
        with next(get_session()) as session:  # type: Session
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
                session.flush()
                loan_id = loan.id
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
        return redirect(url_for("views.loan_edit", loan_id=loan_id))

    # GET
    with next(get_session()) as session:  # type: Session
        loan = session.get(LoanORM, loan_id) if loan_id is not None else None
        insts = []
        remaining = 0.0
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
            last_date = session.execute(
                select(func.max(InstallmentORM.due_date)).where(InstallmentORM.loan_id == loan.id)
            ).scalar_one()
        return render_template("loan_edit.html", loan=loan, installments=insts, remaining=remaining, last_date=last_date)


@bp.post("/loan/<int:loan_id>/installments/add")
def add_inst(loan_id: int):
    due_date = request.form.get("due_date", "")
    amount = float(request.form.get("amount", 0) or 0)
    if amount <= 0:
        flash("Сумма должна быть больше нуля", "error")
        return redirect(url_for("views.loan_edit", loan_id=loan_id))
    with next(get_session()) as session:  # type: Session
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


@bp.post("/loan/<int:loan_id>/installments/<int:inst_id>/toggle")
def toggle_inst(loan_id: int, inst_id: int):
    action = request.form.get("action", "toggle")
    with next(get_session()) as session:  # type: Session
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
    with next(get_session()) as session:  # type: Session
        loan = session.get(LoanORM, loan_id)
        if loan:
            session.delete(loan)
    flash("Кредит удален", "success")
    return redirect(url_for("views.index"))
