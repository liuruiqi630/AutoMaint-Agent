import mysql.connector

# 使用 with 语句，代码块执行完毕后自动关闭连接
with mysql.connector.connect(
    host="localhost",
    user="root",
    password="123456"
) as conn:
    print("是否连接成功:", conn.is_connected())
    
    # 你可以在这里进行数据库操作
    # cursor = conn.cursor()
    # cursor.execute("SHOW DATABASES;")
    # ...

# 离开了 with 的缩进块，连接就已经被自动关闭了
print("已退出 with 代码块，连接已被自动断开。")