import streamlit as st
import pandas as pd
import io
from typing import List

st.set_page_config(page_title="Ghép CKH/KKH & Lọc theo SOL/Chi nhánh", layout="wide")
st.title("📦 Ghép 20 file CKH/KKH ➜ 🔎 Lọc theo SOL / Chi nhánh")

# ---------- Helpers ----------
def read_any(file, tag:str):
    name = file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(file, dtype=str)
    elif name.endswith(".xlsx"):
        df = pd.read_excel(file, dtype=str, engine="openpyxl")
    elif name.endswith(".xls"):
        df = pd.read_excel(file, dtype=str)  # cần xlrd nếu lỗi .xls cũ
    else:
        st.error(f"File không hỗ trợ: {file.name}")
        return None
    df["__SOURCE__"] = file.name
    df["__TYPE__"] = tag  # CKH / KKH
    return df

def find_branch_col(cols: List[str]) -> str:
    # Ưu tiên các tên cột thường gặp
    candidates = ["BRCD", "SOL", "BRANCH", "CHI_NHANH", "MA_CN", "BR_CODE"]
    up = {c.upper(): c for c in cols}
    for c in candidates:
        if c in up:
            return up[c]
    # fallback: chọn cột đầu tiên dạng object
    for c in cols:
        return c
    return None

# ---------- Upload ----------
st.subheader("1) Tải lên tối đa 20 file mỗi nhóm")
c1, c2 = st.columns(2)
with c1:
    files_ckh = st.file_uploader("📁 Chọn file CKH (tối đa 20)", type=["csv","xlsx","xls"], accept_multiple_files=True, key="ckh")
with c2:
    files_kkh = st.file_uploader("📁 Chọn file KKH (tối đa 20)", type=["csv","xlsx","xls"], accept_multiple_files=True, key="kkh")

# ---------- Read & concat ----------
dfs = []
if files_ckh:
    for f in files_ckh[:20]:
        df = read_any(f, "CKH")
        if df is not None:
            dfs.append(df)

if files_kkh:
    for f in files_kkh[:20]:
        df = read_any(f, "KKH")
        if df is not None:
            dfs.append(df)

if not dfs:
    st.info("⬆️ Hãy tải lên các file CKH/KKH để bắt đầu.")
    st.stop()

full_df = pd.concat(dfs, ignore_index=True)

# ---------- Chọn cột BRCD / SOL ----------
st.subheader("2) Chọn cột dùng để lọc (mặc định tự nhận BRCD/SOL)")
default_col = find_branch_col(full_df.columns.tolist())
branch_col = st.selectbox("Cột dùng để lọc:", options=list(full_df.columns), index=list(full_df.columns).index(default_col) if default_col in full_df.columns else 0)

# ---------- Nhập điều kiện lọc ----------
st.subheader("3) Nhập SOL hoặc tên chi nhánh để lọc")
hint = "Ví dụ: 1201,1205 hoặc HANOI; có thể nhập nhiều, ngăn cách bởi dấu phẩy"
raw = st.text_input("Nhập SOL / Chi nhánh:", placeholder=hint).strip()
exact_sol = st.checkbox("🔒 Khớp **chính xác** với SOL (áp dụng cho token là số)", value=False)

def build_mask(series: pd.Series, query: str, exact: bool):
    # series là cột branch_col
    s = series.astype(str).str.upper()
    tokens = [t.strip().upper() for t in query.split(",") if t.strip()]
    if not tokens:
        return pd.Series([True]*len(series))
    mask = pd.Series([False]*len(series))
    for t in tokens:
        if exact and t.isdigit():
            mask = mask | (s == t)
        else:
            mask = mask | s.str.contains(t, na=False)
    return mask

mask = build_mask(full_df[branch_col], raw, exact_sol)
filtered = full_df[mask].copy()

# ---------- Hiển thị ----------
st.success(f"Đã ghép {len(dfs)} bảng • Tổng dòng: {len(full_df):,} • Sau lọc: {len(filtered):,}")
with st.expander("👀 Xem dữ liệu đã ghép (chưa lọc)"):
    st.dataframe(full_df, use_container_width=True, height=300)
st.subheader("📊 Kết quả sau lọc")
st.dataframe(filtered, use_container_width=True, height=420)

# ---------- Download ----------
def to_excel_bytes(df: pd.DataFrame) -> bytes:
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="DATA")
    bio.seek(0)
    return bio.read()

c3, c4 = st.columns(2)
with c3:
    st.download_button(
        "📥 Tải Excel: Dữ liệu đã ghép",
        data=to_excel_bytes(full_df),
        file_name="ALL_CKH_KKH_GHEP.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
with c4:
    st.download_button(
        "📥 Tải Excel: Kết quả lọc",
        data=to_excel_bytes(filtered),
        file_name="FILTERED_CKH_KKH.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
