from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FloatField, SelectField, FileField, BooleanField
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
    remember = BooleanField("تذكرني")
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
    submit = SubmitField("بحث")