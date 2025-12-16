import streamlit as st
import pandas as pd
import io

# --- 页面配置 ---
st.set_page_config(page_title="供应商比价系统", layout="centered")

# --- 模拟数据库 ---
# 如果是第一次启动，初始化一些默认产品，方便演示
if 'data' not in st.session_state:
    st.session_state.data = {
        '光纤连接器 Type-A': {'bids': []},
        '路由器外壳 CNC': {'bids': []}
    }

# --- 核心逻辑：计算排名 ---
def get_product_rankings(product_name):
    """
    计算某个产品的排名。
    逻辑：每个供应商取其最低的一次报价，然后按价格从低到高排序。
    """
    if product_name not in st.session_state.data:
        return []
        
    bids = st.session_state.data[product_name]['bids']
    if not bids:
        return []
    
    # 1. 找到每个供应商的最低报价 (去重)
    supplier_best = {}
    for bid in bids:
        sup = bid['supplier']
        price = bid['price']
        # 如果是该供应商第一次出现，或者比之前的更低，则更新
        if sup not in supplier_best or price < supplier_best[sup]['price']:
            supplier_best[sup] = bid

    # 2. 转换为列表并排序 (价格低 -> 高)
    ranked_list = sorted(supplier_best.values(), key=lambda x: x['price'])
    return ranked_list

# --- 登录逻辑 ---
def login_page():
    st.title("🔐 供应商竞价系统登录")
    with st.form("login_form"):
        username = st.text_input("账号")
        password = st.text_input("密码", type="password")
        submitted = st.form_submit_button("登录")
        
        if submitted:
            # 简单验证
            if username == "admin" and password == "admin888":
                st.session_state.user_type = "admin"
                st.session_state.user = username
                st.rerun()
            elif username in ["supA", "supB", "supC"] and password == "123":
                st.session_state.user_type = "supplier"
                st.session_state.user = username
                st.rerun()
            else:
                st.error("账号或密码错误！(测试用: admin/admin888, supA/123)")

# --- 供应商界面 ---
def supplier_dashboard():
    current_user = st.session_state.user
    st.sidebar.title(f"👤 供应商: {current_user}")
    if st.sidebar.button("退出登录"):
        st.session_state.clear()
        st.rerun()

    st.title("📊 实时报价大厅")

    # 检查是否有产品
    if not st.session_state.data:
        st.info("👋 甲方暂未发布任何询价产品，请稍后再来。")
        return

    for product_name, info in st.session_state.data.items():
        with st.container():
            st.markdown(f"### 📦 {product_name}")
            
            # 获取当前排名数据
            rankings = get_product_rankings(product_name)
            
            # 计算全场最低价
            min_price = rankings[0]['price'] if rankings else 0
            
            # 计算当前用户的排名和价格
            my_rank = None
            my_best_price = None
            
            for idx, rank_info in enumerate(rankings):
                if rank_info['supplier'] == current_user:
                    my_rank = idx + 1 # 排名从1开始
                    my_best_price = rank_info['price']
                    break
            
            # --- 界面显示 ---
            col1, col2, col3 = st.columns([1, 1, 2])
            
            # 1. 显示全场最低
            col1.metric("全场最低价", f"¥{min_price}" if min_price else "--")
            
            # 2. 显示我的状态
            if my_rank == 1:
                col2.metric("我的排名", "第 1 名 🏆", delta="当前领先", delta_color="normal")
            elif my_rank:
                diff = my_best_price - min_price
                col2.metric("我的排名", f"第 {my_rank} 名", delta=f"比最低贵 ¥{diff:.2f}", delta_color="inverse")
            else:
                col2.metric("我的排名", "未报价")

            # 3. 报价输入区
            with col3:
                # 使用 key 避免组件冲突
                with st.form(key=f"form_{product_name}"):
                    new_price = st.number_input("输入报价", min_value=0.0, step=1.0, label_visibility="collapsed")
                    if st.form_submit_button("🚀 提交报价"):
                        if new_price > 0:
                            st.session_state.data[product_name]['bids'].append({
                                'supplier': current_user,
                                'price': new_price,
                                'time': pd.Timestamp.now().strftime('%H:%M:%S')
                            })
                            st.success("报价成功！")
                            st.rerun()
            st.divider()

# --- 管理员界面 (新增产品管理功能) ---
def admin_dashboard():
    st.sidebar.title("👮‍♂️ 管理员模式")
    if st.sidebar.button("退出登录"):
        st.session_state.clear()
        st.rerun()

    st.title("📋 甲方总控台")
    
    # 增加了一个 Tab：产品管理
    tab1, tab2, tab3 = st.tabs(["🏆 实时排名", "⚙️ 产品管理 (新增/删除)", "📝 历史记录"])

    # --- Tab 1: 实时排名视图 ---
    with tab1:
        if not st.session_state.data:
            st.info("暂无产品，请去“产品管理”添加。")
        
        for p_name in st.session_state.data.keys():
            st.subheader(f"📦 {p_name}")
            rankings = get_product_rankings(p_name)
            
            if rankings:
                rank_data = []
                for i, r in enumerate(rankings):
                    rank_data.append({
                        "排名": f"第 {i+1} 名 {'🥇' if i==0 else ''}",
                        "供应商": r['supplier'],
                        "最终报价": f"¥ {r['price']}",
                        "报价时间": r['time']
                    })
                st.table(rank_data)
            else:
                st.caption("等待供应商报价...")
            st.divider()

    # --- Tab 2: 产品管理 (新增功能) ---
    with tab2:
        st.header("发布新的询价产品")
        
        # 1. 添加产品表单
        with st.form("add_product_form"):
            new_product_name = st.text_input("请输入产品名称 (例如：5G芯片散热片)")
            submit_add = st.form_submit_button("➕ 立即发布")
            
            if submit_add:
                if new_product_name:
                    if new_product_name not in st.session_state.data:
                        # 初始化新产品数据
                        st.session_state.data[new_product_name] = {'bids': []}
                        st.success(f"成功发布：{new_product_name}")
                        st.rerun()
                    else:
                        st.warning("该产品已经存在了！")
                else:
                    st.warning("名称不能为空")
        
        st.divider()
        st.subheader("管理现有产品")
        
        # 2. 删除产品列表
        if not st.session_state.data:
            st.text("当前没有任何产品。")
        
        # 转换为列表以避免在迭代时修改字典报错
        for p_name in list(st.session_state.data.keys()):
            col_text, col_btn = st.columns([4, 1])
            col_text.markdown(f"**{p_name}**")
            # 为每个删除按钮设置唯一的 key
            if col_btn.button("🗑️ 删除", key=f"del_{p_name}"):
                del st.session_state.data[p_name]
                st.success(f"已删除：{p_name}")
                st.rerun()
            st.markdown("---")

    # --- Tab 3: 历史流水账 ---
    with tab3:
        all_records = []
        for pname, info in st.session_state.data.items():
            for bid in info['bids']:
                all_records.append({
                    '产品': pname,
                    '供应商': bid['supplier'],
                    '价格': bid['price'],
                    '时间': bid['time']
                })
        
        if all_records:
            df = pd.DataFrame(all_records)
            st.dataframe(df, use_container_width=True)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 导出所有记录", buffer.getvalue(), "bids_history.xlsx")
        else:
            st.warning("暂无数据")

# --- 主程序逻辑 ---
if 'user' not in st.session_state:
    login_page()
else:
    if st.session_state.user_type == "admin":
        admin_dashboard()
    else:
        supplier_dashboard()
