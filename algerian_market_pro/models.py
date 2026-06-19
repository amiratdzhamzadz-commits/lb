from datetime import datetime
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
    login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    
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
    chat_rooms = db.relationship("ChatRoom", backref="machine_ref", lazy="dynamic", cascade="all, delete-orphan")

    def average_rating(self):
        ratings = [r.rating for r in self.reviews.all() if r.rating]
        if ratings:
            return round(sum(ratings) / len(ratings), 1)
        return 0

    def primary_image(self):
        img = MachineImage.query.filter_by(machine_id=self.id, is_primary=True).first()
        if img:
            return img.filename
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ========== Chat System Models ==========

class ChatRoom(db.Model):
    __tablename__ = "chat_room"
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machine.id"), nullable=True, default=0)
    buyer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow)

    buyer = db.relationship("User", foreign_keys=[buyer_id], backref="chat_rooms_as_buyer")
    seller = db.relationship("User", foreign_keys=[seller_id], backref="chat_rooms_as_seller")
    messages = db.relationship("ChatMessage", backref="room", lazy="dynamic", cascade="all, delete-orphan")


class ChatMessage(db.Model):
    __tablename__ = "chat_message"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("chat_room.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    receiver = db.relationship("User", foreign_keys=[receiver_id], backref="received_messages")

    images = db.relationship("ChatImage", backref="message", lazy="dynamic", cascade="all, delete-orphan")
    documents = db.relationship("ChatDocument", backref="message", lazy="dynamic", cascade="all, delete-orphan")
    location = db.relationship("ChatLocation", backref="message", uselist=False, cascade="all, delete-orphan")


class ChatImage(db.Model):
    __tablename__ = "chat_image"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    message_id = db.Column(db.Integer, db.ForeignKey("chat_message.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChatDocument(db.Model):
    __tablename__ = "chat_document"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    original_name = db.Column(db.String(200), nullable=False)
    message_id = db.Column(db.Integer, db.ForeignKey("chat_message.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChatLocation(db.Model):
    __tablename__ = "chat_location"
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    message_id = db.Column(db.Integer, db.ForeignKey("chat_message.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)