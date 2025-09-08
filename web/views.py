from __future__ import annotations
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import date

from app.db import init_db
from app.repository import (
    get_all_loans,
    get_next_payment_for_loan,
    get_installments_total,
    get_installments_unpaid_total,
    get_last_installment_date,
    list_installments,
    add_installment,
    delete_installment,
    mark_installment_paid,
    add_loan,
    update_loan,
    delete_loan,
    recalc_loan_amount_due,
    update_loan_paid_status_if_complete,
)
from app.models import Loan

bp = Blueprint("views", __name__)


@bp.before_app_first_request
def _setup_db():
    init_db()


@bp.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@bp.route("/")
def index():
    loans = get_all_loans()
    enriched = []
    for l in loans:
        unpaid = get_installments_unpaid_total(l.id)
        derived_paid = unpaid == 0
        nxt = None if derived_paid else get_next_payment_for_loan(l)
        last_date = get_last_installment_date(l.id)
        total_due = get_installments_total(l.id)
        enriched.append({
            "loan": l,
            "next_date": nxt[0] if nxt else None,
            "next_amount": nxt[1] if nxt else None,
            "remaining": unpaid,
            "last_date": last_date,
            "paid": derived_paid,
        })
    # Sort by next_date
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
        if loan_id is None:
            new_id = add_loan(Loan(
                id=None,
                website=website,
                loan_date=loan_date,
                amount_borrowed=amount_borrowed,
                amount_due=0.0,
                due_date=due_date,
                risky_org=bool(risky_org),
                notes=notes,
                payment_methods=payment_methods,
                reminded_pre_due=False,
                created_at="",
                is_paid=False,
                org_name=org_name,
            ))
            recalc_loan_amount_due(new_id)
            update_loan_paid_status_if_complete(new_id)
            flash("Кредит создан", "success")
            return redirect(url_for("views.loan_edit", loan_id=new_id))
        else:
            update_loan(Loan(
                id=loan_id,
                website=website,
                loan_date=loan_date,
                amount_borrowed=amount_borrowed,
                amount_due=0.0,
                due_date=due_date,
                risky_org=bool(risky_org),
                notes=notes,
                payment_methods=payment_methods,
                reminded_pre_due=False,
                created_at="",
                is_paid=(get_installments_unpaid_total(loan_id) == 0),
                org_name=org_name,
            ))
            recalc_loan_amount_due(loan_id)
            update_loan_paid_status_if_complete(loan_id)
            flash("Сохранено", "success")
            return redirect(url_for("views.loan_edit", loan_id=loan_id))

    # GET
    loan = None
    insts = []
    remaining = 0.0
    last_date = None
    if loan_id is not None:
        # Find loan in list
        for l in get_all_loans():
            if l.id == loan_id:
                loan = l
                break
        insts = list_installments(loan_id)
        remaining = get_installments_unpaid_total(loan_id)
        last_date = get_last_installment_date(loan_id)
    return render_template("loan_edit.html", loan=loan, installments=insts, remaining=remaining, last_date=last_date)


@bp.post("/loan/<int:loan_id>/installments/add")
def add_inst(loan_id: int):
    due_date = request.form.get("due_date", "")
    amount = float(request.form.get("amount", 0) or 0)
    if amount <= 0:
        flash("Сумма должна быть больше нуля", "error")
        return redirect(url_for("views.loan_edit", loan_id=loan_id))
    add_installment(type("I", (), {
        "id": None,
        "loan_id": loan_id,
        "due_date": due_date,
        "amount": amount,
        "paid": False,
        "paid_date": None,
        "created_at": "",
    })())
    recalc_loan_amount_due(loan_id)
    update_loan_paid_status_if_complete(loan_id)
    flash("Платеж добавлен", "success")
    return redirect(url_for("views.loan_edit", loan_id=loan_id))


@bp.post("/loan/<int:loan_id>/installments/<int:inst_id>/toggle")
def toggle_inst(loan_id: int, inst_id: int):
    action = request.form.get("action", "toggle")
    if action == "delete":
        delete_installment(inst_id)
        flash("Платеж удален", "success")
    else:
        # naive toggle: read desired state from form
        new_paid = request.form.get("paid") == "1"
        paid_date_val = date.today().isoformat() if new_paid else None
        mark_installment_paid(inst_id, new_paid, paid_date_val)
        flash("Статус платежа обновлен", "success")
    recalc_loan_amount_due(loan_id)
    update_loan_paid_status_if_complete(loan_id)
    return redirect(url_for("views.loan_edit", loan_id=loan_id))


@bp.post("/loan/<int:loan_id>/delete")
def delete_loan_route(loan_id: int):
    delete_loan(loan_id)
    flash("Кредит удален", "success")
    return redirect(url_for("views.index"))
