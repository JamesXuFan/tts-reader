# =====================================================
# 数据库模型定义（数据表结构）
#
# 什么是ORM模型？
# ORM（对象关系映射）让我们用Python类来描述数据库表的结构
# 每个类 = 一张数据表
# 每个类属性 = 表中的一列
# 每个类实例 = 表中的一行记录
#
# 表结构设计：
# ┌─────────┐      ┌────────────┐      ┌───────────┐
# │  users  │ 1──∞ │   groups   │ 1──∞ │ favorites │
# └─────────┘      └────────────┘      └───────────┘
#                                            │
#                                       ┌────▼────┐
#                                       │tts_cache│
#                                       └─────────┘
# =====================================================

from sqlalchemy import (
    Column, Integer, String, Text, Boolean,
    DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base


# =====================================================
# 用户表（users）
# =====================================================
class User(Base):
    """
    用户表：存储注册用户的账号信息

    字段说明：
    - id：主键，自动递增，唯一标识每个用户
    - username：用户名，不允许重复
    - email：邮箱，不允许重复，未来可用于找回密码
    - hashed_password：密码的哈希值（绝对不能存明文密码！）
    - is_active：账号是否激活，可用于封禁用户
    - created_at：注册时间，自动记录
    """
    __tablename__ = "users"  # 对应数据库中的表名

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    email = Column(String(100), unique=True, nullable=False, index=True, comment="邮箱")
    hashed_password = Column(String(255), nullable=False, comment="哈希加密后的密码")
    is_active = Column(Boolean, default=True, comment="账号是否激活")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="注册时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="最后更新时间")

    # 关联关系：一个用户可以有多个分组
    # back_populates="owner" 表示在Group模型中有一个名为owner的属性指回User
    # cascade="all, delete-orphan" 表示删除用户时自动删除其所有分组
    groups = relationship("Group", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        """方便调试时显示对象信息"""
        return f"<User id={self.id} username={self.username}>"


# =====================================================
# 收藏分组表（groups）
# =====================================================
class Group(Base):
    """
    收藏分组表：用户可以创建多个分组来整理收藏

    例如：
    - "英语学习" 分组
    - "诗词朗诵" 分组
    - "日常用语" 分组
    """
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="分组名称")
    description = Column(String(255), nullable=True, comment="分组描述（可选）")
    color = Column(String(20), default="#4A90E2", comment="分组颜色标签，存储HEX颜色代码")
    sort_order = Column(Integer, default=0, comment="排列顺序，数字越小越靠前")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    # 外键：关联到users表的id字段
    # ondelete="CASCADE"：当用户被删除时，其分组也自动删除
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # 关联关系
    owner = relationship("User", back_populates="groups")
    favorites = relationship("Favorite", back_populates="group")

    # 联合唯一约束：同一个用户不能有两个同名分组
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_group_name"),
    )

    def __repr__(self):
        return f"<Group id={self.id} name={self.name} user_id={self.user_id}>"


# =====================================================
# 收藏内容表（favorites）
# =====================================================
class Favorite(Base):
    """
    收藏内容表：存储用户收藏的文字内容

    核心字段是 text_content（要朗读的文字）
    每条收藏可以关联到一个分组，方便分类管理
    """
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False, comment="收藏标题（用户自定义）")
    text_content = Column(Text, nullable=False, comment="要朗读的文字内容")
    language = Column(String(20), default="zh-CN", comment="文字语言代码，如zh-CN/en-US/ja-JP")
    note = Column(String(500), nullable=True, comment="用户备注（可选）")
    is_favorite = Column(Boolean, default=True, comment="是否收藏（用于软删除场景）")
    play_count = Column(Integer, default=0, comment="播放次数统计")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="收藏时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="最后修改时间")

    # 外键
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # group_id 可以为空（nullable=True），表示"未分组"状态
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True)

    # 关联关系
    owner = relationship("User")
    group = relationship("Group", back_populates="favorites")
    # 一条收藏内容可能有多条TTS缓存（不同语音参数生成的音频）
    tts_caches = relationship("TTSCache", back_populates="favorite", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Favorite id={self.id} title={self.title}>"


# =====================================================
# TTS音频缓存表（tts_cache）
# =====================================================
class TTSCache(Base):
    """
    TTS音频缓存表：缓存已生成的音频，避免重复调用API

    为什么要缓存？
    - 调用Gemini API有费用和速率限制
    - 相同的文字+相同语音参数，每次生成的结果是一样的
    - 缓存后直接返回，速度更快，成本更低

    audio_data：存储Base64编码的音频数据
    （因为SQLite不擅长存储二进制，用Base64编码转成文本存储）
    """
    __tablename__ = "tts_cache"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # 缓存键：由文字内容+语音参数生成的哈希值，用于快速查找
    cache_key = Column(String(64), unique=True, nullable=False, index=True, comment="缓存唯一标识（MD5哈希）")
    text_content = Column(Text, nullable=False, comment="原始文字内容")
    language = Column(String(20), nullable=False, comment="语言代码")
    voice_name = Column(String(100), nullable=True, comment="使用的声音名称")
    audio_data = Column(Text, nullable=False, comment="Base64编码的音频数据")
    audio_format = Column(String(20), default="mp3", comment="音频格式")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="缓存创建时间")
    # 收藏ID（可选）：如果这个缓存是从某条收藏生成的，记录关联关系
    favorite_id = Column(Integer, ForeignKey("favorites.id", ondelete="SET NULL"), nullable=True)

    # 关联关系
    favorite = relationship("Favorite", back_populates="tts_caches")

    def __repr__(self):
        return f"<TTSCache id={self.id} cache_key={self.cache_key[:8]}...>"
