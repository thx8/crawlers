import pymysql
import config as all_config


def update(data):
    try:
        # 建立数据库连接
        connection = pymysql.connect(
            host=all_config.MYSQL_HOST,
            user=all_config.MYSQL_USER,
            password=all_config.MYSQL_PASSWORD,
            database=all_config.MYSQL_DATABASE,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

        with connection.cursor() as cursor:
            # 假设 itemid 是 data 中的一个字段
            itemid = data.get('itemid')
            if not itemid:
                print("Error: itemid is required in data")
                return None

            # 查询 itemid 是否存在
            sql_check = "SELECT 1 FROM browse WHERE itemid = %s"
            cursor.execute(sql_check, (itemid,))
            result = cursor.fetchone()

            if result:
                # itemid 存在，执行更新
                update_clause = ', '.join([f"{key}=%s" for key in data.keys()])
                sql = f"UPDATE browse SET {update_clause} WHERE itemid = %s"
                values = list(data.values()) + [itemid]
            else:
                # itemid 不存在，执行插入
                fields = ', '.join(data.keys())
                placeholders = ', '.join(['%s'] * len(data))
                sql = f"INSERT INTO browse ({fields}) VALUES ({placeholders})"
                values = list(data.values())

            # 执行 SQL
            affected_rows = cursor.execute(sql, values)

            # 提交事务
            connection.commit()

            return affected_rows

    except pymysql.MySQLError as e:
        print(f"Error: {e}")
        return None
    finally:
        if connection:
            connection.close()