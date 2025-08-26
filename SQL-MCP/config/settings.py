from functools import lru_cache
from typing import Literal, Optional, ClassVar, Dict

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings

"""
Literals[] 表示一个枚举类型，用于限制变量的值只能是这些值中的一个。
"""
DBType = Literal["mysql", "postgresql", "oracle", "mssql"]


class Settings(BaseSettings):
    """
    项目全局配置类，从环境变量加载数据库配置。
    支持 MySQL、PostgreSQL、Oracle、MSSQL。
    """

    # ===== 通用数据库配置 =====
    DB_TYPE: DBType = Field("mysql", description="数据库类型")
    DB_HOST: str = Field("127.0.0.1", description="数据库主机")
    DB_PORT: Optional[int] = Field(None, description="数据库端口（可选）")
    DB_USER: str = Field("root", description="数据库用户名")
    DB_PASSWORD: SecretStr = Field("root", description="数据库密码")
    DB_NAME: str = Field("test_db", description="数据库名")
    DB_SERVICE_NAME: str = Field("", description="Oracle 服务名（可选，优先于 DB_NAME）")

    # ===== 可选参数 =====
    DB_CHARSET: str = Field("utf8mb4", description="MySQL 字符集")
    DB_DRIVER: Optional[str] = Field(None, description="数据库驱动（如 MSSQL 可指定）")

    # ===== 内部映射表 =====
    _PORT_MAP: ClassVar[Dict[str, int]] = {
        "mysql": 3306,
        "postgresql": 5432,
        "oracle": 1521,
        "mssql": 1433,
    }

    _DEFAULT_DRIVER: ClassVar[Dict[str, str]] = {
        "mssql": "ODBC+Driver+17+for+SQL+Server"
    }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @field_validator("DB_PORT", mode="before")
    def set_default_port(cls, v, values):
        """根据 DB_TYPE 设置默认端口"""
        if v:
            return int(v)
        db_type: DBType = values.data.get("DB_TYPE", "mysql")
        return cls._PORT_MAP.get(db_type)

    @field_validator("DB_PASSWORD", mode="before")
    def ensure_secret_str(cls, v):
        """确保密码是 SecretStr 类型"""
        return v if isinstance(v, SecretStr) else SecretStr(str(v))

    # ===== 动态生成连接 URL =====
    def get_db_url(self) -> str:
        password = self.DB_PASSWORD.get_secret_value()
        base = dict(
            user=self.DB_USER,
            password=password,
            host=self.DB_HOST,
            port=self.DB_PORT,
            db=self.DB_NAME,
        )

        if self.DB_TYPE == "mysql":
            return (
                f"mysql+pymysql://{base['user']}:{base['password']}"
                f"@{base['host']}:{base['port']}/{base['db']}?charset={self.DB_CHARSET}"
            )

        if self.DB_TYPE == "postgresql":
            return (
                f"postgresql+psycopg2://{base['user']}:{base['password']}"
                f"@{base['host']}:{base['port']}/{base['db']}"
            )

        if self.DB_TYPE == "oracle":
            service = self.DB_SERVICE_NAME or base["db"]
            conn_str = f"{base['host']}:{base['port']}/{service}"
            return f"oracle+cx_oracle://{base['user']}:{base['password']}@{conn_str}"

        if self.DB_TYPE == "mssql":
            driver = self.DB_DRIVER or self._DEFAULT_DRIVER["mssql"]
            return (
                f"mssql+pyodbc://{base['user']}:{base['password']}"
                f"@{base['host']}:{base['port']}/{base['db']}?driver={driver}"
            )

        raise ValueError(f"Unsupported DB_TYPE: {self.DB_TYPE}")


# ===== 缓存配置 =====
@lru_cache()
def get_settings() -> Settings:
    """获取缓存的全局配置实例"""
    return Settings()


# ===== 快捷方法 =====
def get_db_url() -> str:
    """快捷获取数据库连接字符串"""
    return get_settings().get_db_url()


"""
__all__ 模块的“白名单”导出表,在其他 模块中使用 import * 语法时，只导入 __all__ 中定义的变量。
"""
__all__ = ["BaseSettings", "Settings", "DBType", "get_settings", "get_db_url", "SecretStr"]
