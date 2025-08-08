import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Ghép CKH/KKH", layout="wide")
st.title("📦 Ghép CKH/KKH ➜ 🔎 Lọc theo SOL / Chi nhánh")
st.caption("Debug mode: sẽ hiện lỗi nếu có")

@st.cache_data(show_spinner=False)
def read_any_cached(bytes_data: bytes, name: str, tag: str):
    try:
        bio = io.BytesIO(bytes_data)
        lname = name.lower()
        if lname.endswith(".csv"):
            df = pd.read_csv(bio, dtype=str)
        elif lname.endswith(".xlsx"):
            df = pd.read_excel(bio, dtype=str, engine="openpyxl")
        elif lname.endswith(".xls"):
            df = pd.read_excel(bio, dtype=str, engine="xlrd")  # cần xlrd==1.2.0
        else:
            raise ValueError(f"Định dạng không hỗ trợ: {name}")
        df["__SOURCE__"] = name
        df["__TYPE__"] = tag
        return df
    except Exception as e:
        st.error(f"Lỗi khi đọc file: {name}")
        st.exception(e)
        return None

c1, c2 = st.columns(2)
with c1:
    files_ckh = st.file_uploader("📁 CKH (nhiều file)", type=["csv","xlsx","xls"], accept_multiple_files=True, key="ckh")
with c2:
    files_kkh = st.file_uploader("📁 KKH (nhiều file)", type=["csv","xlsx","xls"], accept_multiple_files=True, key="kkh")

dfs, total = [], (len(files_ckh or []) + len(files_kkh or []))
if total == 0:
    st.info("⬆️ Tải lên các file để bắt đầu.")
    st.stop()

pbar = st.progress(0.0, text="Đang đọc dữ liệu…")
done = 0
for tag, files in [("CKH", files_ckh or []), ("KKH", files_kkh or [])]:
    for f in files:
        df = read_any_cached(f.getvalue(), f.name, tag)
        if df is not None:
            dfs.append(df)
        done += 1
        pbar.progress(done/total, text=f"Đang đọc: {f.name}")

if not dfs:
    st.error("Không đọc được file nào. Kiểm tra định dạng/requirements.")
    st.stop()

full_df = pd.concat(dfs, ignore_index=True)

def pick_branch_col(cols):
    cands = ["BRCD","SOL","BRANCH","CHI_NHANH","MA_CN","BR_CODE"]
    up = {c.upper(): c for c in cols}
    for k in cands:
        for real in cols:
            if real.upper()==k: return real
    return cols[0]

branch_col = st.selectbox("Cột dùng để lọc:", list(full_df.columns),
                          index=list(full_df.columns).index(pick_branch_col(full_df.columns)))
raw = st.text_input("Nhập SOL/Chi nhánh (ví dụ: 1201,1205 hoặc HANOI):").strip()
exact_sol = st.checkbox("🔒 Khớp chính xác khi token là số", value=False)

def build_mask(series, query, exact):
    s = series.astype(str).str.upper()
    tokens = [t.strip().upper() for t in query.split(",") if t.strip()]
    if not tokens: return pd.Series(True, index=s.index)
    m = pd.Series(False, index=s.index)
    for t in tokens:
        if exact and t.isdigit():
            m |= (s == t)
        else:
            m |= s.str.contains(t, na=False)
    return m

filtered = full_df[build_mask(full_df[branch_col], raw, exact_sol)]
st.success(f"Đã ghép {len(dfs)} bảng • Tổng dòng: {len(full_df):,} • Sau lọc: {len(filtered):,}")
st.dataframe(filtered, use_container_width=True, height=450)

def to_excel_bytes(df):
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="DATA")
    bio.seek(0); return bio.read()

c3, c4 = st.columns(2)
c3.download_button("📥 Tải ALL (ghép)", data=to_excel_bytes(full_df),
                   file_name="ALL_CKH_KKH_GHEP.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
c4.download_button("📥 Tải FILTER (đã lọc)", data=to_excel_bytes(filtered),
                   file_name="FILTERED_CKH_KKH.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
