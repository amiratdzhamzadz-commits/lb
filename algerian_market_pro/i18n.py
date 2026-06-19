#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    نظام الترجمة المتعدد اللغات - Multi-Language i18n System
"""
import os, json
from flask import request, session, g

# اللغات المتاحة
SUPPORTED_LANGUAGES = {
    'ar': {
        'name': 'العربية',
        'dir': 'rtl',
        'font': 'Cairo',
        'bootstrap': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.rtl.min.css',
        'flag': '🇩🇿'
    },
    'en': {
        'name': 'English',
        'dir': 'ltr',
        'font': 'Poppins',
        'bootstrap': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
        'flag': '🇬🇧'
    },
    'fr': {
        'name': 'Français',
        'dir': 'ltr',
        'font': 'Poppins',
        'bootstrap': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
        'flag': '🇫🇷'
    }
}

DEFAULT_LANGUAGE = 'ar'

# تحميل ملفات الترجمة
_translations = {}

def load_translations():
    """تحميل جميع ملفات الترجمة من مجلد translations"""
    global _translations
    trans_dir = os.path.join(os.path.dirname(__file__), 'translations')
    if not os.path.exists(trans_dir):
        os.makedirs(trans_dir, exist_ok=True)
        return

    for lang in SUPPORTED_LANGUAGES:
        filepath = os.path.join(trans_dir, f'{lang}.json')
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    _translations[lang] = json.load(f)
            except Exception as e:
                print(f"⚠️ خطأ في تحميل ملف الترجمة {lang}: {e}")
                _translations[lang] = {}
        else:
            _translations[lang] = {}

    print(f"✅ تم تحميل الترجمات: {', '.join(_translations.keys())}")

def get_language_info(lang_code):
    """الحصول على معلومات اللغة"""
    return SUPPORTED_LANGUAGES.get(lang_code, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])

def get_locale():
    """اكتشاف اللغة المناسبة حسب الترتيب التالي:
    1. لغة محفوظة في الجلسة
    2. معامل ?lang= في URL
    3. رأس Accept-Language من المتصفح
    4. اللغة الافتراضية (العربية)
    """
    # 1. التحقق من وجود لغة في الجلسة
    if 'lang' in session:
        lang = session['lang']
        if lang in SUPPORTED_LANGUAGES:
            return lang

    # 2. التحقق من معامل URL
    lang = request.args.get('lang', '')
    if lang in SUPPORTED_LANGUAGES:
        session['lang'] = lang
        return lang

    # 3. الكشف التلقائي من رأس المتصفح Accept-Language
    accept_lang = request.headers.get('Accept-Language', '')
    lang_priority = ['ar', 'fr', 'en']
    for lang_code in lang_priority:
        if lang_code in accept_lang.lower():
            session['lang'] = lang_code
            return lang_code

    # 4. الكشف حسب البلد
    cf_country = request.headers.get('CF-IPCountry', '')
    geo_country = request.headers.get('X-Geo-Country', '')
    country = (cf_country or geo_country or '').upper()
    if country in ['DZ']:
        session['lang'] = 'ar'
        return 'ar'
    if country in ['FR', 'BE', 'CH', 'CA', 'MC']:
        session['lang'] = 'fr'
        return 'fr'

    # 5. اللغة الافتراضية
    session['lang'] = DEFAULT_LANGUAGE
    return DEFAULT_LANGUAGE

def _(key, **kwargs):
    """دالة الترجمة - تستخدم في القوالب"""
    # إذا كنا خارج سياق التطبيق، نعيد المفتاح كما هو
    try:
        lang = getattr(g, 'current_lang', DEFAULT_LANGUAGE)
    except RuntimeError:
        lang = DEFAULT_LANGUAGE

    # الحصول على النص المترجم
    translations = _translations.get(lang, {})
    text = translations.get(key, key)

    # إذا لم نجد الترجمة، نبحث في اللغة الافتراضية
    if text == key and lang != DEFAULT_LANGUAGE:
        default_trans = _translations.get(DEFAULT_LANGUAGE, {})
        text = default_trans.get(key, key)

    # تطبيق المتغيرات في النص
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass

    return text

def get_all_languages():
    """الحصول على قائمة بكل اللغات المدعومة"""
    return [(code, info['name'], info['flag']) for code, info in SUPPORTED_LANGUAGES.items()]

# تهيئة الترجمات عند استيراد الوحدة
load_translations()