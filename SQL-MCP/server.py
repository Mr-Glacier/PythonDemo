from config.settings import *

if __name__ == '__main__':
    settings = get_settings()
    # 使用配置项
    print(f"当前数据库类型：{settings.DB_TYPE}")
    print(f"数据库主机：{settings.DB_HOST}")
    print(f"数据库用户名：{settings.DB_USER}")

    # 如果需要密码（注意：生产环境尽量避免打印密码）
    password = settings.DB_PASSWORD.get_secret_value()
    print(f"数据库密码：{password}")  # 仅用于调试，实际项目中不要这样做
