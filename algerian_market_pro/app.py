#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    سوق الماكينات الجزائري PRO - النسخة الكاملة مع دعم متعدد اللغات
"""
import os, secrets, re, json, random, io, html
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlparse, urljoin

from flask import (Flask, render_template, redirect, url_for, flash, request,
                   jsonify, abort, send_file, session, g)
from flask_login import (LoginManager, login_user, logout_user, login_required, current_user)
from flask_mail import Mail, Message
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect, generate_csrf
from werkzeug.utils import secure_filename
from PIL import Image
import openpyxl
from dotenv import load_dotenv

load_dotenv()

from config import Config
from models import (db, User, Machine, MachineImage, Review, Favorite, 
                    Report, Notification, ChatMessage, ChatRoom, ChatImage, ChatDocument, ChatLocation)
from forms import RegistrationForm, LoginForm, MachineForm, SearchForm
from i18n import _, get_locale, get_language_info, get_all_languages, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = _("flash_login_required")
login_manager.session_protection = "strong"

mail = Mail(app)
cache = Cache(app)

limiter = Limiter(app=app, key_func=get_remote_address,
                  default_limits=["200 per day", "50 per hour"],
                  storage_uri="memory://")

csp = {
    'default-src': ["'self'"],
    'script-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net",
                   "https://code.jquery.com", "https://cdnjs.cloudflare.com",
                   "https://cdn.leafletjs.com"],
    'style-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net",
                  "https://cdnjs.cloudflare.com", "https://fonts.googleapis.com",
                  "https://unpkg.com", "https://cdn.leafletjs.com"],
    'img-src': ["'self'", "data:", "blob:", "https://*.tile.openstreetmap.org",
                "https://unpkg.com", "https://cdn.leafletjs.com"],
    'font-src': ["'self'", "https://cdnjs.cloudflare.com", "https://fonts.gstatic.com"],
    'connect-src': ["'self'"],
    'frame-src': ["'self'"]
}

# Only enable Talisman in production with HTTPS
if not app.debug and not app.config.get('TESTING'):
    Talisman(app, content_security_policy=csp, force_https=True,
             strict_transport_security=True, strict_transport_security_max_age=31536000)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_DOC_EXTENSIONS = {"pdf", "doc", "docx", "xls", "xlsx", "txt", "ppt", "pptx"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_DOC_SIZE = 10 * 1024 * 1024

UPLOAD_FOLDER_ABS = os.path.join(os.getcwd(), 'static', 'uploads')
CHAT_IMAGES_DIR = os.path.join('static', 'uploads', 'chat_images')
CHAT_DOCS_DIR = os.path.join('static', 'uploads', 'chat_documents')

os.makedirs(UPLOAD_FOLDER_ABS, exist_ok=True)
os.makedirs(CHAT_IMAGES_DIR, exist_ok=True)
os.makedirs(CHAT_DOCS_DIR, exist_ok=True)

def allowed_file(filename):
    if "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_doc(filename):
    if "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in ALLOWED_DOC_EXTENSIONS

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc

def sanitize_html(text):
    return html.escape(str(text), quote=True) if text else ""

def save_picture(form_picture):
    if not form_picture or (hasattr(form_picture, "filename") and form_picture.filename == ""):
        return None
    form_picture.seek(0, os.SEEK_END)
    if form_picture.tell() > MAX_IMAGE_SIZE:
        return None
    form_picture.seek(0)
    random_hex = secrets.token_hex(16)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext.lower()
    picture_path = os.path.join(UPLOAD_FOLDER_ABS, picture_fn)
    try:
        i = Image.open(form_picture)
        i.verify()
        form_picture.seek(0)
        i = Image.open(form_picture)
        i.thumbnail((800, 800))
        i.save(picture_path, optimize=True, quality=85)
        return picture_fn
    except Exception:
        return None

def save_chat_image(file_data, filename):
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else "png"
    random_name = secrets.token_hex(16) + "." + ext
    path = os.path.join(CHAT_IMAGES_DIR, random_name)
    try:
        img = Image.open(file_data)
        img.verify()
        file_data.seek(0)
        img = Image.open(file_data)
        img.thumbnail((600, 600))
        img.save(path, optimize=True, quality=80)
        return random_name
    except Exception:
        return None

def save_chat_document(file_data, filename):
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else "bin"
    random_name = secrets.token_hex(16) + "." + ext
    path = os.path.join(CHAT_DOCS_DIR, random_name)
    try:
        file_data.save(path)
        return random_name
    except Exception:
        return None

def create_slug(text):
    text = re.sub(r"[^\w\s-]", "", str(text).strip())
    text = re.sub(r"\s+", "-", text)[:80].lower()
    orig, c = text, 1
    while Machine.query.filter_by(slug=text).first():
        text = f"{orig}-{c}"
        c += 1
    return text

def send_email(subject, recipients, body):
    try:
        msg = Message(subject, recipients=recipients, body=body)
        mail.send(msg)
        return True
    except Exception as e:
        app.logger.error(f"Email error: {e}")
        return False

def admin_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if not current_user.is_authenticated or current_user.role != "admin":
            abort(403)
        return f(*a, **kw)
    return dec

@app.before_request
def before_request():
    g.current_lang = get_locale()
    g.lang_info = get_language_info(g.current_lang)
    g.all_languages = get_all_languages()

@app.context_processor
def inject_now():
    return {"now": datetime.utcnow()}

@app.context_processor
def inject_lang():
    return {
        "current_lang": g.get('current_lang', DEFAULT_LANGUAGE),
        "lang_info": g.get('lang_info', get_language_info(DEFAULT_LANGUAGE)),
        "all_languages": g.get('all_languages', get_all_languages()),
        "SUPPORTED_LANGUAGES": SUPPORTED_LANGUAGES,
        "_": _
    }

@app.context_processor
def inject_unread():
    if current_user.is_authenticated:
        cnt = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        chat_unr = ChatMessage.query.filter(ChatMessage.receiver_id == current_user.id, ChatMessage.is_read == False).count()
        return {"unread_count": cnt, "chat_unread_count": chat_unr}
    return {"unread_count": 0, "chat_unread_count": 0}

@app.context_processor
def inject_csrf():
    return dict(csrf_token=generate_csrf())

@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(429)
def ratelimit_handler(e):
    flash(_("طلبات كثير جداً. يرجى التهدئة قليلاً."), "danger")
    return redirect(url_for("home"))

@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return render_template("500.html"), 500

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/language/<lang_code>")
def set_language(lang_code):
    if lang_code in SUPPORTED_LANGUAGES:
        session['lang'] = lang_code
        g.current_lang = lang_code
        g.lang_info = get_language_info(lang_code)
    referrer = request.referrer
    if referrer and is_safe_url(referrer):
        return redirect(referrer)
    return redirect(url_for("home"))

@app.route("/")
def home():
    featured = Machine.query.filter_by(status="approved", is_featured=True).order_by(Machine.created_at.desc()).limit(6).all()
    latest = Machine.query.filter_by(status="approved").order_by(Machine.created_at.desc()).limit(12).all()
    total_machines = Machine.query.filter_by(status="approved").count()
    total_users = User.query.count()
    total_categories = 8
    total_wilayas = 58
    return render_template("index.html", featured=featured, latest=latest,
                          total_machines=total_machines, total_users=total_users,
                          total_categories=total_categories, total_wilayas=total_wilayas)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = sanitize_html(request.form.get("name", ""))
        email = sanitize_html(request.form.get("email", ""))
        message = sanitize_html(request.form.get("message", ""))
        if name and email and message:
            send_email(_("nav_new_ad") + " - " + _("site_name"), ["admin@market.dz"],
                       f"{_('contact_name')}: {name}\n{_('contact_email')}: {email}\n{_('contact_message')}: {message}")
            flash(_("contact_success"), "success")
        else:
            flash("يرجى ملء جميع الحقول", "danger")
        return redirect(url_for("contact"))
    return render_template("contact.html")

@app.route("/search")
def search():
    page = request.args.get("page", 1, type=int)
    form = SearchForm()
    q, w, cat = request.args.get("q", ""), request.args.get("wilaya", ""), request.args.get("category", "")
    min_p = request.args.get("min_price", 0, type=float)
    max_p = request.args.get("max_price", 0, type=float)
    machines = Machine.query.filter_by(status="approved")
    if q:
        machines = machines.filter(Machine.name.ilike(f"%{q}%") | Machine.description.ilike(f"%{q}%"))
    if w:
        machines = machines.filter_by(wilaya=w)
    if cat:
        machines = machines.filter_by(category=cat)
    if min_p:
        machines = machines.filter(Machine.price >= min_p)
    if max_p:
        machines = machines.filter(Machine.price <= max_p)
    pag = machines.order_by(Machine.created_at.desc()).paginate(page=page, per_page=Config.ITEMS_PER_PAGE, error_out=False)
    return render_template("search.html", form=form, machines=pag.items, pagination=pag, query=q)

@app.route("/search/live")
@limiter.limit("30 per minute")
def live_search():
    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        return jsonify([])
    machines = Machine.query.filter(Machine.status == "approved",
        (Machine.name.ilike(f"%{q}%") | Machine.description.ilike(f"%{q}%"))
    ).order_by(Machine.views.desc()).limit(5).all()
    return jsonify([{
        "id": m.id, "name": m.name, "slug": m.slug,
        "price": m.price, "wilaya": m.wilaya,
        "image": m.primary_image(), "views": m.views
    } for m in machines])

@app.route("/machine/<slug>")
def machine_detail(slug):
    machine = Machine.query.filter_by(slug=slug).first_or_404()
    if not session.get(f"viewed_{machine.id}"):
        machine.views += 1
        session[f"viewed_{machine.id}"] = True
        db.session.commit()
    related = Machine.query.filter_by(category=machine.category, status="approved").filter(Machine.id != machine.id).limit(4).all()
    page = request.args.get("reviews_page", 1, type=int)
    rp = machine.reviews.order_by(Review.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template("machine_detail.html", machine=machine, related=related, reviews_page=rp)

@app.route("/machine/<slug>/reviews")
def machine_reviews(slug):
    machine = Machine.query.filter_by(slug=slug).first_or_404()
    page = request.args.get("page", 1, type=int)
    rp = machine.reviews.order_by(Review.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template("machine_detail.html", machine=machine,
                          related=Machine.query.filter_by(category=machine.category, status="approved").filter(Machine.id != machine.id).limit(4).all(),
                          reviews_page=rp)

@app.route("/new", methods=["GET", "POST"])
@login_required
def new_machine():
    form = MachineForm()
    if form.validate_on_submit():
        machine = Machine(name=sanitize_html(form.name.data), slug=create_slug(form.name.data),
                         description=sanitize_html(form.description.data), price=form.price.data,
                         wilaya=form.wilaya.data, category=form.category.data,
                         phone=sanitize_html(form.phone.data) if form.phone.data else current_user.phone,
                         user_id=current_user.id)
        db.session.add(machine)
        db.session.flush()
        first, uploaded = True, 0
        for img in request.files.getlist("images"):
            if uploaded >= 10:
                break
            if img and allowed_file(img.filename):
                fn = save_picture(img)
                if fn:
                    db.session.add(MachineImage(filename=fn, is_primary=first, machine_id=machine.id))
                    first, uploaded = False, uploaded + 1
        db.session.commit()
        for adm in User.query.filter_by(role="admin").all():
            db.session.add(Notification(title=_("nav_new_ad"), message=f"{_('flash_ad_created')}: {machine.name}", user_id=adm.id))
        db.session.commit()
        flash(_("flash_ad_created"), "success")
        return redirect(url_for("seller_dashboard"))
    return render_template("create_machine.html", form=form)

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    form = RegistrationForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash("البريد الإلكتروني مستخدم بالفعل", "danger")
            return render_template("register.html", form=form)
        if User.query.filter_by(username=form.username.data).first():
            flash("اسم المستخدم مستخدم بالفعل", "danger")
            return render_template("register.html", form=form)
        user = User(username=sanitize_html(form.username.data), email=form.email.data.lower().strip(),
                    phone=sanitize_html(form.phone.data) if form.phone.data else "")
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        try:
            send_email(_("register_success") + " - " + _("site_name"), [user.email],
                       _("register_success") + " " + user.username + "!\n\n" + _("site_tagline"))
        except:
            pass
        login_user(user)
        flash(_("register_success"), "success")
        return redirect(url_for("home"))
    return render_template("register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per 15 minutes")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            if user.locked_until and user.locked_until > datetime.utcnow():
                flash("حسابك مقفل مؤقتاً. يرجى المحاولة لاحقاً.", "danger")
                return render_template("login.html", form=form)
            login_user(user, remember=form.remember.data if hasattr(form, 'remember') else False)
            user.login_attempts = 0
            user.locked_until = None
            db.session.commit()
            np = request.args.get("next")
            if np and is_safe_url(np):
                return redirect(np)
            flash(_("flash_logged_in"), "success")
            return redirect(url_for("home"))
        else:
            if user:
                user.login_attempts = (user.login_attempts or 0) + 1
                if user.login_attempts >= 5:
                    user.locked_until = datetime.utcnow() + timedelta(minutes=15)
                db.session.commit()
            flash("بريد إلكتروني أو كلمة مرور خاطئة", "danger")
    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash(_("flash_logged_out"), "success")
    return redirect(url_for("home"))

@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    page = request.args.get("page", 1, type=int)
    machines = Machine.query.order_by(Machine.created_at.desc()).paginate(page=page, per_page=Config.ITEMS_PER_PAGE, error_out=False)
    return render_template("admin_dashboard.html", machines=machines.items, pagination=machines,
                          pending_count=Machine.query.filter_by(status="pending").count(),
                          total_users=User.query.count(), total_machines=Machine.query.count(),
                          active_chats=ChatRoom.query.count())

@app.route("/admin/reports")
@login_required
@admin_required
def admin_reports():
    page = request.args.get("page", 1, type=int)
    reports = Report.query.order_by(Report.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template("admin_reports.html", reports=reports.items, pagination=reports)

@app.route("/admin/users")
@login_required
@admin_required
def admin_users():
    page = request.args.get("page", 1, type=int)
    users = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template("admin_users.html", users=users.items, pagination=users)

@app.route("/admin/approve/<int:machine_id>")
@login_required
@admin_required
def approve_machine(machine_id):
    machine = Machine.query.get_or_404(machine_id)
    machine.status = "approved"
    db.session.commit()
    notif = Notification(title=_("flash_ad_approved"), message=f"{_('flash_ad_approved')}: {machine.name}", user_id=machine.user_id)
    db.session.add(notif)
    db.session.commit()
    flash(_("flash_ad_approved"), "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/reject/<int:machine_id>")
@login_required
@admin_required
def reject_machine(machine_id):
    machine = Machine.query.get_or_404(machine_id)
    machine.status = "rejected"
    db.session.commit()
    notif = Notification(title=_("flash_ad_rejected"), message=f"{_('flash_ad_rejected')}: {machine.name}", user_id=machine.user_id)
    db.session.add(notif)
    db.session.commit()
    flash(_("flash_ad_rejected"), "danger")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/feature/<int:machine_id>")
@login_required
@admin_required
def feature_machine(machine_id):
    machine = Machine.query.get_or_404(machine_id)
    machine.is_featured = not machine.is_featured
    db.session.commit()
    flash(_("admin_feature"), "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/seller")
@login_required
def seller_dashboard():
    page = request.args.get("page", 1, type=int)
    machines = Machine.query.filter_by(user_id=current_user.id).order_by(Machine.created_at.desc()).paginate(page=page, per_page=Config.ITEMS_PER_PAGE, error_out=False)
    total_views = sum(m.views for m in current_user.machines.all())
    total_clicks = sum(m.whatsapp_clicks for m in current_user.machines.all())
    approved = Machine.query.filter_by(user_id=current_user.id, status="approved").count()
    total = Machine.query.filter_by(user_id=current_user.id).count()
    rate = round((approved / total * 100), 1) if total > 0 else 0
    labels = json.dumps([(datetime.utcnow() - timedelta(days=i)).strftime("%d/%m") for i in range(29, -1, -1)])
    data = json.dumps([random.randint(0, 15) for _ in range(30)])
    return render_template("seller_dashboard.html", machines=machines.items, pagination=machines,
                          total_views=total_views, total_clicks=total_clicks,
                          approved=approved, total=total, approval_rate=rate,
                          chart_labels=labels, chart_data=data)

@app.route("/seller/export")
@login_required
def seller_export():
    machines = Machine.query.filter_by(user_id=current_user.id).order_by(Machine.created_at.desc()).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = _("nav_my_ads")
    ws.append([_("label_name"), f"{_('label_price')} (DZD)", _("label_views"), _("label_status"), _("label_date")])
    for m in machines:
        ws.append([m.name, m.price, m.views, m.status, m.created_at.strftime("%Y-%m-%d")])
    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return send_file(out, as_attachment=True, download_name=f"{_('nav_my_ads')}.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route("/machine/edit/<int:machine_id>", methods=["GET", "POST"])
@login_required
def edit_machine(machine_id):
    machine = Machine.query.get_or_404(machine_id)
    if machine.user_id != current_user.id and current_user.role != "admin":
        abort(403)
    form = MachineForm(obj=machine)
    if form.validate_on_submit():
        machine.name = sanitize_html(form.name.data)
        machine.description = sanitize_html(form.description.data)
        machine.price = form.price.data
        machine.wilaya = form.wilaya.data
        machine.category = form.category.data
        machine.phone = sanitize_html(form.phone.data) if form.phone.data else ""
        machine.status = "pending"
        db.session.commit()
        flash(_("flash_ad_created"), "success")
        return redirect(url_for("seller_dashboard"))
    return render_template("create_machine.html", form=form, edit=True, machine=machine)

@app.route("/machine/delete/<int:machine_id>", methods=["POST"])
@login_required
def delete_machine(machine_id):
    machine = Machine.query.get_or_404(machine_id)
    if machine.user_id != current_user.id and current_user.role != "admin":
        abort(403)
    db.session.delete(machine)
    db.session.commit()
    flash(_("تم الحذف بنجاح"), "success")
    return redirect(url_for("seller_dashboard"))

@app.route("/whatsapp/<int:machine_id>")
def whatsapp_contact(machine_id):
    m = Machine.query.get_or_404(machine_id)
    phone = m.phone or (User.query.get(m.user_id).phone if m.user_id else "")
    if phone:
        m.whatsapp_clicks += 1
        db.session.commit()
        return redirect(f"https://wa.me/{phone.replace('+','').replace(' ','')}?text={_('Hi, I am interested in the machine')}: {m.name}")
    flash("رقم الهاتف غير متوفر", "danger")
    return redirect(url_for("machine_detail", slug=m.slug))

@app.route("/favorite/<int:machine_id>", methods=["POST"])
@login_required
def toggle_favorite(machine_id):
    f = Favorite.query.filter_by(user_id=current_user.id, machine_id=machine_id).first()
    if f:
        db.session.delete(f)
        db.session.commit()
        return jsonify({"status": "removed"})
    db.session.add(Favorite(user_id=current_user.id, machine_id=machine_id))
    db.session.commit()
    return jsonify({"status": "added"})

@app.route("/my_favorites")
@login_required
def my_favorites():
    faves = Favorite.query.filter_by(user_id=current_user.id).order_by(Favorite.created_at.desc()).all()
    machines = [f.machine for f in faves if f.machine and f.machine.status == "approved"]
    return render_template("favorites.html", machines=machines)

@app.route("/notifications")
@login_required
def notifications():
    page = request.args.get("page", 1, type=int)
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template("notifications.html", notifications=notifs.items, pagination=notifs)

@app.route("/notifications/read/<int:notif_id>")
@login_required
def mark_notification_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id != current_user.id:
        abort(403)
    notif.is_read = True
    db.session.commit()
    return jsonify({"status": "ok"})

@app.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    flash(_("notifications_mark_read"), "success")
    return redirect(url_for("notifications"))

@app.route("/chat")
@login_required
def chat_index():
    if current_user.role == "admin":
        rooms = ChatRoom.query.order_by(ChatRoom.last_message_at.desc()).all()
    else:
        rooms = ChatRoom.query.filter(
            (ChatRoom.buyer_id == current_user.id) | (ChatRoom.seller_id == current_user.id)
        ).order_by(ChatRoom.last_message_at.desc()).all()
    return render_template("chat_index.html", rooms=rooms)

@app.route("/chat/<int:machine_id>")
@login_required
def chat_with_seller(machine_id):
    machine = Machine.query.get_or_404(machine_id)
    if machine.user_id == current_user.id:
        flash("لا يمكنك مراسلة نفسك", "warning")
        return redirect(url_for("machine_detail", slug=machine.slug))
    room = ChatRoom.query.filter_by(machine_id=machine.id, buyer_id=current_user.id, seller_id=machine.user_id).first()
    if not room:
        room = ChatRoom(machine_id=machine.id, buyer_id=current_user.id, seller_id=machine.user_id)
        db.session.add(room)
        db.session.commit()
    messages = ChatMessage.query.filter_by(room_id=room.id).order_by(ChatMessage.created_at.asc()).all()
    for msg in ChatMessage.query.filter_by(room_id=room.id, receiver_id=current_user.id, is_read=False).all():
        msg.is_read = True
    db.session.commit()
    return render_template("chat_room.html", room=room, messages=messages, machine=machine)

@app.route("/chat/send/<int:room_id>", methods=["POST"])
@login_required
@csrf.exempt
def send_message(room_id):
    room = ChatRoom.query.get_or_404(room_id)
    if current_user.id not in [room.buyer_id, room.seller_id] and current_user.role != "admin":
        abort(403)
    content = sanitize_html(request.form.get("content", "").strip())
    if not content or len(content) > 2000:
        return jsonify({"error": "الرسالة فارغة أو طويلة جداً"}), 400
    receiver_id = room.seller_id if current_user.id == room.buyer_id else room.buyer_id
    msg = ChatMessage(content=content, room_id=room.id, sender_id=current_user.id, receiver_id=receiver_id)
    room.last_message_at = datetime.utcnow()
    db.session.add(msg)
    db.session.commit()
    return jsonify({"status": "ok", "message": {"id": msg.id, "content": msg.content, "sender_id": msg.sender_id,
                                                "created_at": msg.created_at.isoformat(), "sender_name": current_user.username}})

@app.route("/chat/messages/<int:room_id>")
@login_required
def get_messages(room_id):
    room = ChatRoom.query.get_or_404(room_id)
    if current_user.id not in [room.buyer_id, room.seller_id] and current_user.role != "admin":
        abort(403)
    since_id = request.args.get("since", 0, type=int)
    msgs = ChatMessage.query.filter(ChatMessage.room_id == room.id, ChatMessage.id > since_id).order_by(ChatMessage.created_at.asc()).all()
    return jsonify([{"id": m.id, "content": m.content, "sender_id": m.sender_id,
                     "sender_name": User.query.get(m.sender_id).username if User.query.get(m.sender_id) else "مستخدم",
                     "created_at": m.created_at.isoformat(), "is_mine": m.sender_id == current_user.id} for m in msgs])

@app.route("/chat/upload/<int:room_id>", methods=["POST"])
@login_required
@csrf.exempt
def chat_upload(room_id):
    room = ChatRoom.query.get_or_404(room_id)
    if current_user.id not in [room.buyer_id, room.seller_id] and current_user.role != "admin":
        abort(403)
    if 'file' not in request.files:
        return jsonify({"error": "لم يتم إرسال ملف"}), 400
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"error": "الملف فارغ"}), 400
    receiver_id = room.seller_id if current_user.id == room.buyer_id else room.buyer_id
    msg = ChatMessage(content="[ملف]", room_id=room.id, sender_id=current_user.id, receiver_id=receiver_id)
    db.session.add(msg)
    db.session.flush()
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
    if ext in ALLOWED_EXTENSIONS:
        filename = save_chat_image(file, file.filename)
        if filename:
            chat_img = ChatImage(filename=filename, message_id=msg.id)
            db.session.add(chat_img)
            msg.content = "🖼️ [صورة]"
    elif ext in ALLOWED_DOC_EXTENSIONS:
        filename = save_chat_document(file, file.filename)
        if filename:
            chat_doc = ChatDocument(filename=filename, original_name=file.filename, message_id=msg.id)
            db.session.add(chat_doc)
            msg.content = f"📄 [مستند: {sanitize_html(file.filename)}]"
    else:
        db.session.rollback()
        return jsonify({"error": "نوع الملف غير مدعوم"}), 400
    room.last_message_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"status": "ok", "message": {"id": msg.id, "content": msg.content, "sender_id": msg.sender_id,
                                                "created_at": msg.created_at.isoformat(), "sender_name": current_user.username}})

@app.route("/chat/unread-count")
@login_required
def chat_unread_count():
    return jsonify({"count": ChatMessage.query.filter(ChatMessage.receiver_id == current_user.id,
                                                       ChatMessage.is_read == False).count()})

@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(role="admin").first():
            admin = User(username="admin", email="admin@market.dz", role="admin", is_verified=True)
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("✅ تم إنشاء المدير: admin@market.dz / admin123")

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)