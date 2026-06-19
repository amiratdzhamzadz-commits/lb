#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Algerian Industrial Market PRO - Full Project Generator
"""
import os, secrets

PROJECT = "algerian_market_pro"

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    base = PROJECT
    for d in [f"{base}/templates", f"{base}/static/css", f"{base}/static/js", f"{base}/static/icons", f"{base}/uploads"]:
        os.makedirs(d, exist_ok=True)
    create_file(f"{base}/.env", f"""SECRET_KEY={secrets.token_hex(32)}
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_DEFAULT_SENDER=your_email@gmail.com
DATABASE_URL=sqlite:///site.db""")
    create_file(f"{base}/requirements.txt", """Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-Mail==0.10.0
Flask-Limiter==3.5.0
Flask-Talisman==1.1.0
Flask-Caching==2.1.0
Flask-WTF==1.2.1
WTForms==3.1.2
email-validator==2.1.1
Pillow==10.3.0
openpyxl==3.1.2
python-dotenv==1.0.1
blinker==1.7.0
gunicorn==22.0.0""")
    create_file(f"{base}/README.md", """# Market PRO
Full marketplace platform.""")
    create_file(f"{base}/config.py", """import os
from dotenv import load_dotenv
load_dotenv()
class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(32))
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///site.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = "200/day"
    UPLOAD_FOLDER = "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ITEMS_PER_PAGE = 20""")
    create_file(f"{base}/models.py", """from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
db = SQLAlchemy()
class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="seller")
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)
    machines = db.relationship("Machine", backref="seller", lazy="dynamic")
    reviews = db.relationship("Review", backref="author", lazy="dynamic")
    favorites = db.relationship("Favorite", backref="user", lazy="dynamic")
    reports = db.relationship("Report", backref="reporter", lazy="dynamic")
    notifications = db.relationship("Notification", backref="user", lazy="dynamic")
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
class Machine(db.Model):
    __tablename__ = "machine"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(250), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    wilaya = db.Column(db.String(50), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    phone = db.Column(db.String(20))
    status = db.Column(db.String(20), default="pending", index=True)
    views = db.Column(db.Integer, default=0)
    whatsapp_clicks = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    images = db.relationship("MachineImage", backref="machine", lazy="dynamic", cascade="all, delete-orphan")
    reviews = db.relationship("Review", backref="machine", lazy="dynamic", cascade="all, delete-orphan")
    favorites = db.relationship("Favorite", backref="machine", lazy="dynamic", cascade="all, delete-orphan")
    reports = db.relationship("Report", backref="machine", lazy="dynamic", cascade="all, delete-orphan")
    def average_rating(self):
        ratings = [r.rating for r in self.reviews.all() if r.rating]
        if ratings: return round(sum(ratings) / len(ratings), 1)
        return 0
    def primary_image(self):
        img = MachineImage.query.filter_by(machine_id=self.id, is_primary=True).first()
        if img: return img.filename
        first = self.images.first()
        return first.filename if first else "default.jpg"
class MachineImage(db.Model):
    __tablename__ = "machine_image"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    machine_id = db.Column(db.Integer, db.ForeignKey("machine.id"), nullable=False)
class Review(db.Model):
    __tablename__ = "review"
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    reply = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey("machine.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class Favorite(db.Model):
    __tablename__ = "favorite"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey("machine.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("user_id", "machine_id"),)
class Report(db.Model):
    __tablename__ = "report"
    id = db.Column(db.Integer, primary_key=True)
    reason = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey("machine.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class Notification(db.Model):
    __tablename__ = "notification"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)""")
    create_file(f"{base}/forms.py", """from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FloatField, SelectField, FileField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange, Optional
WILAYAS = ["Adrar","Chlef","Laghouat","Oum El Bouaghi","Batna","Bejaia","Biskra","Bechar","Blida","Bouira","Tamanrasset","Tebessa","Tlemcen","Tiaret","Tizi Ouzou","Alger","Djelfa","Jijel","Setif","Saida","Skikda","Sidi Bel Abbes","Annaba","Guelma","Constantine","Medea","Mostaganem","M'Sila","Mascara","Ouargla","Oran","El Bayadh","Illizi","Bordj Bou Arreridj","Boumerdes","El Tarf","Tindouf","Tissemsilt","El Oued","Khenchela","Souk Ahras","Tipaza","Mila","Ain Defla","Naama","Ain Temouchent","Ghardaia","Relizane","Timimoun","Bordj Badji Mokhtar","Ouled Djellal","Beni Abbes","In Salah","In Guezzam","Touggourt","Djanet","El M'Ghair","El Meniaa"]
CATEGORIES = ["الماكينات الزراعية","الماكينات الصناعية","معدات البناء","معدات النقل","معدات المطاعم","معدات طبية","أدوات كهربائية","أخرى"]
class RegistrationForm(FlaskForm):
    username = StringField("اسم المستخدم", validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField("البريد الإلكتروني", validators=[DataRequired(), Email()])
    password = PasswordField("كلمة المرور", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField("تأكيد كلمة المرور", validators=[DataRequired(), EqualTo("password")])
    phone = StringField("رقم الهاتف", validators=[Optional(), Length(max=20)])
    submit = SubmitField("تسجيل")
class LoginForm(FlaskForm):
    email = StringField("البريد الإلكتروني", validators=[DataRequired(), Email()])
    password = PasswordField("كلمة المرور", validators=[DataRequired()])
    submit = SubmitField("دخول")
class MachineForm(FlaskForm):
    name = StringField("اسم الماكينة", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("الوصف", validators=[DataRequired()])
    price = FloatField("السعر (دج)", validators=[DataRequired(), NumberRange(min=0)])
    wilaya = SelectField("الولاية", choices=[("", "اختر الولاية")] + [(w,w) for w in WILAYAS], validators=[DataRequired()])
    category = SelectField("الفئة", choices=[("", "اختر الفئة")] + [(c,c) for c in CATEGORIES], validators=[DataRequired()])
    phone = StringField("رقم الهاتف (اختياري)", validators=[Optional(), Length(max=20)])
    images = FileField("صور الماكينة", validators=[Optional()])
    submit = SubmitField("نشر الإعلان")
class SearchForm(FlaskForm):
    query = StringField("بحث", validators=[Optional()])
    wilaya = SelectField("الولاية", choices=[("", "الكل")] + [(w,w) for w in WILAYAS], validators=[Optional()])
    category = SelectField("الفئة", choices=[("", "الكل")] + [(c,c) for c in CATEGORIES], validators=[Optional()])
    min_price = FloatField("أقل سعر", validators=[Optional(), NumberRange(min=0)])
    max_price = FloatField("أعلى سعر", validators=[Optional(), NumberRange(min=0)])
    submit = SubmitField("بحث")""")
    print("✅ Done! Folder:", base)

if __name__ == "__main__":
    main()