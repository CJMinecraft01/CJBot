from main import db


class ReactionRole(db.Model):
    ReactionRoleId = db.Column(db.Integer, primary_key=True)
    GuildId = db.Column(db.Integer, nullable=False)
    ChannelId = db.Column(db.Integer, nullable=False)
    MessageId = db.Column(db.Integer, nullable=False)
    EmojiName = db.Column(db.Text, nullable=False)
    EmojiAnimated = db.Column(db.Boolean, nullable=False)
    EmojiId = db.Column(db.Integer, nullable=True)
    RoleId = db.Column(db.Integer, nullable=False)
    ReactionRoleType = db.Column(db.Integer, nullable=False)


class ServerOptions(db.Model):
    GuildId = db.Column(db.Integer, primary_key=True)
    AdminRoleId = db.Column(db.Integer)
