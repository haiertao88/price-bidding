import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import time

# ==========================================
# 1. 数据库配置与初始化函数
# ==========================================
DB_FILE = 'procurement.db'

def init_db():
    """初始化数据库表结构和测试数据"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 创建表：供应商
    c.execute('''CREATE TABLE IF NOT EXISTS suppliers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  username TEXT UNIQUE, 
                  password TEXT, 
                  name TEXT, 
                  category TEXT)''')
    
    # 创建表：询价项目
    c.execute('''CREATE TABLE IF NOT EXISTS inquiries
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  title TEXT, 
                  details TEXT,
                  project_password TEXT, 
                  create_date TEXT, 
                  deadline TEXT, 
                  status TEXT)''')
    
    # 创建表：报价记录
    c.execute('''CREATE TABLE IF NOT EXISTS quotes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  inquiry_id INTEGER, 
                  supplier_username TEXT, 
                  price REAL, 
                  delivery_days INTEGER, 
                  remarks TEXT,
                  timestamp TEXT)''')

    # --- 预埋测试数据 ---
    # 检查是否已有供应商，没有则插入您指定的供应商账号
    c.execute("SELECT count(*) FROM suppliers")
    if c.fetchone()[0] == 0:
        suppliers_data = [
            ('GYSA', '123456', '供应商A (线缆)', '优质'),
            ('GYSB', '123456', '供应商B (连接器)', '普通'),
            ('GYSC', '123456', '供应商C (机柜)', '优质')
        ]
        c.executemany("INSERT INTO suppliers (username, password, name, category) VALUES (?,?,?,?)", suppliers_data)
        print("已初始化供应商数据")

    conn.commit()
    conn.close()

# 执行初始化
init_db()

# ==========================================
# 2. 数据库操作通用函数
# ==========================================
def run_query(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(query, params)
    if fetch:
        data = c.fetchall()
        columns = [description[0] for description in c.description]
        conn.close()
        return pd.DataFrame(data, columns=columns)
    else:
        conn.commit()
        conn.close()
        return None

# ==========================================
# 3. 界面逻辑：登录页
# ==========================================
def login_page():
    st.markdown("<h1 style='text-align: center;'>供应链询价管理系统</h1>", unsafe_allow_html=True)
    st.write("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.subheader("🔐 系统登录")
            role = st.selectbox("选择角色", ["甲方管理员", "供应商"])
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            
            if st.button("登录", use_container_width=True):
                # 甲方登录逻辑 (硬编码校验)
                if role == "甲方管理员":
                    if username == "HUAMAI" and password == "HUAMAI888":
                        st.session_state.logged_in = True
                        st.session_state.role = "Admin"
                        st.session_state.username = username
                        st.success("登录成功！")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("管理员账号或密码错误")
                
                # 供应商登录逻辑 (查库校验)
                elif role == "供应商":
                    df = run_query("SELECT * FROM suppliers WHERE username=? AND password=?", (username, password), fetch=True)
                    if not df.empty:
                        st.session_state.logged_in = True
                        st.session_state.role = "Supplier"
                        st.session_state.username = username
                        st.session_state.supplier_name = df.iloc[0]['name']
                        st.success(f"欢迎回来，{df.iloc[0]['name']}")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("供应商账号或密码错误")

# ==========================================
# 4. 界面逻辑：甲方管理员后台
# ==========================================
def admin_dashboard():
    st.sidebar.header(f"👤 管理员: {st.session_state.username}")
    menu = st.sidebar.radio("功能导航", ["发布询价", "报价比对", "供应商列表"])
    
    if st.sidebar.button("退出登录"):
        st.session_state.logged_in = False
        st.rerun()

    # --- 模块：发布询价 ---
    if menu == "发布询价":
        st.header("📄 发布新的询价项目")
        with st.form("create_inquiry"):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("项目标题", placeholder="例如：2025年光纤采购项目")
            with col2:
                pwd = st.text_input("设置项目访问密码", placeholder="供应商需凭此码报价")
            
            details = st.text_area("采购需求详情", placeholder="请输入具体的规格型号、数量要求...")
            deadline = st.date_input("截止日期")
            
            submitted = st.form_submit_button("立即发布")
            if submitted and title and pwd:
                run_query("INSERT INTO inquiries (title, details, project_password, create_date, deadline, status) VALUES (?, ?, ?, ?, ?, ?)",
                          (title, details, pwd, datetime.now().strftime("%Y-%m-%d"), str(deadline), "进行中"))
                st.success("✅ 项目发布成功！")
    
    # --- 模块：报价比对 ---
    elif menu == "报价比对":
        st.header("📊 报价比对分析")
        
        # 获取所有项目
        projects = run_query("SELECT * FROM inquiries", fetch=True)
        if projects.empty:
            st.info("暂无询价项目")
        else:
            selected_project_title = st.selectbox("选择要查看的项目", projects['title'])
            project_id = projects[projects['title'] == selected_project_title]['id'].values[0]
            
            # 获取该项目的报价
            quotes = run_query("SELECT * FROM quotes WHERE inquiry_id=?", (int(project_id),), fetch=True)
            
            if quotes.empty:
                st.warning("该项目暂无供应商报价。")
            else:
                st.subheader("报价明细表")
                st.dataframe(quotes[['supplier_username', 'price', 'delivery_days', 'remarks', 'timestamp']], use_container_width=True)
                
                # 可视化对比
                st.subheader("价格趋势对比")
                st.bar_chart(data=quotes, x='supplier_username', y='price')
                
                # 最低价推荐
                min_price = quotes['price'].min()
                best_supplier = quotes[quotes['price'] == min_price].iloc[0]['supplier_username']
                st.success(f"💡 最低报价供应商：**{best_supplier}**，价格：¥{min_price}")

    # --- 模块：供应商列表 ---
    elif menu == "供应商列表":
        st.header("🏢 注册供应商库")
        df = run_query("SELECT id, username, name, category FROM suppliers", fetch=True)
        st.dataframe(df, use_container_width=True)

# ==========================================
# 5. 界面逻辑：供应商后台
# ==========================================
def supplier_dashboard():
    st.sidebar.header(f"🏢 供应商: {st.session_state.username}")
    st.sidebar.text(f"({st.session_state.get('supplier_name', '')})")
    
    if st.sidebar.button("退出登录"):
        st.session_state.logged_in = False
        st.rerun()

    st.header("📝 在线报价中心")
    
    # 获取所有进行中的项目
    projects = run_query("SELECT * FROM inquiries WHERE status='进行中'", fetch=True)
    
    if projects.empty:
        st.info("当前没有正在进行的询价项目。")
        return

    # 选择项目
    project_options = {row['title']: row for index, row in projects.iterrows()}
    selected_title = st.selectbox("请选择要报价的项目", list(project_options.keys()))
    
    selected_row = project_options[selected_title]
    
    st.info(f"📅 截止日期: {selected_row['deadline']}")
    
    # 密码验证区域
    with st.expander("点击展开报价区域", expanded=True):
        input_pwd = st.text_input("请输入甲方提供的【项目密码】以查看详情", type="password")
        
        if input_pwd == selected_row['project_password']:
            st.divider()
            st.markdown("### 📋 采购需求详情")
            st.write(selected_row['details'])
            
            st.divider()
            st.markdown("### 💰 提交您的报价")
            
            # 检查是否已经报过价
            existing_quote = run_query("SELECT * FROM quotes WHERE inquiry_id=? AND supplier_username=?", 
                                      (selected_row['id'], st.session_state.username), fetch=True)
            
            if not existing_quote.empty:
                st.warning(f"您已对此项目报价：¥{existing_quote.iloc[0]['price']}。再次提交将覆盖旧报价。")

            with st.form("submit_quote"):
                price = st.number_input("总价/单价 (RMB)", min_value=0.0, step=100.0)
                delivery = st.number_input("预计交货期 (天)", min_value=1, step=1)
                remarks = st.text_area("备注 (付款条件/质保等)")
                
                submitted = st.form_submit_button("确认提交报价")
                
                if submitted:
                    # 删除旧报价（如果有）
                    run_query("DELETE FROM quotes WHERE inquiry_id=? AND supplier_username=?", 
                             (selected_row['id'], st.session_state.username))
                    # 插入新报价
                    run_query("INSERT INTO quotes (inquiry_id, supplier_username, price, delivery_days, remarks, timestamp) VALUES (?,?,?,?,?,?)",
                             (selected_row['id'], st.session_state.username, price, delivery, remarks, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    
                    st.success("报价已提交给甲方！")
                    time.sleep(1)
                    st.rerun()
        elif input_pwd:
            st.error("项目密码错误，无法查看详情或报价。")

# ==========================================
# 6. 主程序入口
# ==========================================
def main():
    st.set_page_config(page_title="询价管理系统", layout="wide", page_icon="📊")
    
    # 初始化Session状态
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # 路由控制
    if not st.session_state.logged_in:
        login_page()
    else:
        if st.session_state.role == "Admin":
            admin_dashboard()
        elif st.session_state.role == "Supplier":
            supplier_dashboard()

if __name__ == "__main__":
    main()
