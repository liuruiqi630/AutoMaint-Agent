import mysql.connector
import random
import datetime
from faker import Faker

# 初始化中文 Faker
fake = Faker('zh_CN')

# 1. 连接数据库 (确保你之前已经建好了 lab_system)
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="123456", # 换成你的密码
    database="lab_system"
)
cursor = conn.cursor()

# 2. 创建数据表
# 注意：last_maintenance 用 DATE 类型，status 用来区分设备状态
cursor.execute("""
    CREATE TABLE IF NOT EXISTS equipment (
        id INT AUTO_INCREMENT PRIMARY KEY,
        device_name VARCHAR(100) NOT NULL,
        device_type VARCHAR(50) NOT NULL,
        last_maintenance DATE NOT NULL,
        consumable_stock INT NOT NULL,
        status VARCHAR(20) DEFAULT 'active',
        owner_department VARCHAR(50)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
""")
print("✅ 数据表 equipment 准备就绪！")

# 清空旧数据（每次跑脚本都重新生成）
cursor.execute("TRUNCATE TABLE equipment;")

# 3. 准备生成数据的规则
departments = ['海洋物理部', '海洋化学部', '海洋生物部', '地质勘测部']
device_types = ['CTD采水器', 'ADCP声学多普勒', '温盐深传感器', '荧光计', '离心机', '盐度计']

insert_data = []  # 用于批量插入的列表
today = datetime.date.today()

# 4. 生成 150 条模拟数据
for i in range(150):
    dept = random.choice(departments)
    d_type = random.choice(device_types)
    # 设备命名更有真实感，比如：海洋物理部-P01-CTD采水器
    d_name = f"{dept}-P{random.randint(1, 20):02d}-{d_type}"
    status = 'active'

    # 随机决定这台设备的“命运”
    fate = random.random()

    if fate < 0.15: 
        # 15% 的概率是【极其正常】的设备：昨天刚维护，库存满
        last_date = today - datetime.timedelta(days=random.randint(1, 10))
        stock = random.randint(20, 50)
        status = 'active'
    
    elif fate < 0.35:
        # 20% 的概率是【维护超期】：30天到120天前维护过（触发预警）
        last_date = today - datetime.timedelta(days=random.randint(31, 120))
        stock = random.randint(10, 30)
        status = 'active'

    elif fate < 0.50:
        # 15% 的概率是【耗材告急】：库存 0 到 4 个（触发预警）
        last_date = today - datetime.timedelta(days=random.randint(5, 25))
        stock = random.randint(0, 4)
        status = 'active'

    elif fate < 0.65:
        # 15% 的概率是【又超期又缺耗材】的双重暴击
        last_date = today - datetime.timedelta(days=random.randint(40, 100))
        stock = random.randint(0, 3)
        status = 'active'

    elif fate < 0.80:
        # 15% 的概率是【已报废】：哪怕超期了，也不应该触发预警（考验 Agent 的过滤能力）
        last_date = today - datetime.timedelta(days=random.randint(50, 200))
        stock = 0
        status = 'scrapped' # 报废状态

    elif fate < 0.90:
        # 10% 的概率是【全新设备】：今天刚买，还没维护过，不该报超期
        last_date = today
        stock = 10
        status = 'active'

    else:
        # 10% 的概率是【脏数据】：故意制造幻觉数据，测试代码鲁棒性
        last_date = today + datetime.timedelta(days=5) # 未来日期（数据录入错误）
        stock = -5 # 负数库存（系统bug）
        status = 'active'

    # 将每一条数据组装成元组
    insert_data.append((d_name, d_type, last_date.isoformat(), stock, status, dept))

# 5. 批量执行插入（executemany 速度极快）
sql = """
    INSERT INTO equipment (device_name, device_type, last_maintenance, consumable_stock, status, owner_department) 
    VALUES (%s, %s, %s, %s, %s, %s)
"""
cursor.executemany(sql, insert_data)
conn.commit()

print(f"🎉 成功生成并插入了 {cursor.rowcount} 条设备数据！")
cursor.close()
conn.close()