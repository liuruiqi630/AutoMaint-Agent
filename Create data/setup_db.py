import pymysql

# 1. 连接 MySQL 服务端（注意：这里不指定 database）
conn = pymysql.connect(host='localhost', user='root', password='123456', charset='utf8mb4')
cursor = conn.cursor()

# 2. 创建数据库（务必用 utf8mb4，防中文乱码）
cursor.execute("CREATE DATABASE IF NOT EXISTS lab_system DEFAULT CHARACTER SET utf8mb4;")
print("✅ 数据库 lab_system 创建成功！")

cursor.close()
conn.close()