import streamlit as st
import streamlit_wordcloud as wordcloud
import pandas as pd
import plotly.express as px
import uuid
from google.oauth2 import service_account
from google.cloud import bigquery
from matplotlib import cm
from matplotlib.colors import Normalize, rgb2hex
from datetime import datetime, timedelta
from collections import defaultdict

# 캐시된 데이터 로드
# @st.cache_data
# def load_processed_data():
#     df = pd.read_pickle('data/processed_reviews.pkl')
#     words = pd.read_pickle('data/wordcloud_data.pkl').to_dict('records')
#     return df, words

def get_color(score):
    norm = Normalize(vmin=1, vmax=5)
    cmap = cm.get_cmap('coolwarm')
    rgba = cmap(norm(score))
    return rgb2hex(rgba)

@st.cache_resource
def load_processed_data():
    # BigQuery 클라이언트 설정
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["bigquery"]
    )
    project_id = st.secrets["bigquery"]["project_id"]
    dataset = st.secrets["bigquery"]["dataset"]
    
    client = bigquery.Client(credentials=credentials, project=project_id)
    
    # 전시회 목록 가져오기
    exhibition_query = f"""
    SELECT DISTINCT exhibition_name 
    FROM `{project_id}.{dataset}.reviews`
    """
    exhibitions = client.query(exhibition_query).to_dataframe()
    
    return client, project_id, dataset, exhibitions

def prepare_wordcloud_data(df):
    # 키워드별로 집계
    keyword_count = defaultdict(int)
    keyword_star_sum = defaultdict(float)

    for _, row in df.iterrows():
        keywords = row['keywords']  # 이미 numpy array 형태
        unique_keywords = set(keywords)
        for kw in unique_keywords:
            keyword_count[kw] += 1
            keyword_star_sum[kw] += row['star_rating']

    words = []
    for kw in keyword_count:
        avg_rating = keyword_star_sum[kw] / keyword_count[kw]
        words.append({
            "text": kw,
            "value": keyword_count[kw],
            "avg_rating": round(avg_rating, 2),
            "color": get_color(avg_rating)
        })
    return words

@st.cache_resource
def create_wordcloud(words):
    return wordcloud.visualize(
        words,
        per_word_coloring=True,
        tooltip_data_fields={
            'text': '키워드',
            'value': '빈도',
            'avg_rating': '평균 별점'
        },
        width="100%",
        height="500px"
    )

def main():
    st.title("🎨 전시 리뷰 워드클라우드")
    
    # 데이터 로드
    client, project_id, dataset, exhibitions = load_processed_data()
    
    # 필터 UI
    col1, col2 = st.columns(2)
    with col1:
        selected_exhibition = st.selectbox(
            "전시회 선택",
            options=exhibitions['exhibition_name'].tolist()
        )
    
    with col2:
        date_range = st.date_input(
            "방문 기간",
            value=((datetime.now() - timedelta(days=1)).date(), (datetime.now() - timedelta(days=1)).date()),
            key="date_range"
        )
        start_date, end_date = date_range
    
    # 세션 상태 초기화
    if 'df' not in st.session_state:
        st.session_state.df = None

    if st.button("데이터 조회"):
        
        # 선택된 조건으로 데이터 쿼리
        filter_query = f"""
            SELECT *
            FROM `{project_id}.{dataset}.reviews`
            WHERE exhibition_name = @exhibition
            AND visit_date BETWEEN @start_date AND @end_date
        """
        
        query_params = [
            bigquery.ScalarQueryParameter("exhibition", "STRING", selected_exhibition),
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]
        
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        st.session_state.df = client.query(filter_query, job_config=job_config).to_dataframe()
        
    if st.session_state.df is not None:
        df = st.session_state.df

        if df.empty:
            st.warning("선택한 기간에 해당하는 데이터가 없습니다.")
            return
        
        # 워드클라우드 데이터 준비
        words = prepare_wordcloud_data(df)

        # 세션 상태 초기화
        # if "clicked_word" not in st.session_state:
        #     st.session_state.clicked_word = None
        # if "wordcloud_reset" not in st.session_state:
        #     st.session_state.wordcloud_reset = False

        # # 초기화 버튼
        # if st.session_state.clicked_word:
        #     if st.button("🔄 선택된 키워드 초기화"):
        #         st.session_state.clicked_word = None
        #         st.session_state.wordcloud_reset = True
        #         st.rerun()
        
        # 워드클라우드 키 설정
        # if st.session_state.wordcloud_reset:
        #     wordcloud_key = f"wordcloud_{uuid.uuid4()}"
        #     st.session_state.wordcloud_reset = False
        # else:
        #     wordcloud_key = "wordcloud"

        # st.write("워드클라우드 데이터:", words)  # 디버그용
        
        if not words:  # words가 비어있는지 확인
            st.warning("표시할 키워드가 없습니다.")
            return
        # 워드클라우드 시각화
        selected_word = create_wordcloud(words)

        # 워드클라우드 시각화
        
        # if (
        #     selected_word
        #     and isinstance(selected_word.get("clicked"), dict)
        # ):
        #     st.session_state.clicked_word = selected_word["clicked"]["text"]
        
        # # 클릭된 키워드가 있으면 리뷰 출력
        # if st.session_state.clicked_word:

        # 클릭된 단어 처리
        if selected_word and isinstance(selected_word.get("clicked"), dict):
            clicked_word = selected_word["clicked"]["text"]
            filtered_df = df[df['keywords'].apply(lambda x: clicked_word in x)]
            title = f"'{clicked_word}' 키워드가 포함된 리뷰 별점 분포"

            # 2. value_counts() → dict → DataFrame로 처리
            rating_counts = (
                filtered_df['star_rating']
                .value_counts()
                .to_dict()
            )

            # 3. 누락된 별점 0으로 채우기
            rating_data = [{'star_rating': i, 'count': rating_counts.get(i, 0)} for i in [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]]
            rating_counts_df = pd.DataFrame(rating_data)

                    # Plotly 히스토그램
            fig = px.bar(
                rating_counts_df,
                x='star_rating',
                y='count',
                labels={'star_rating': '별점', 'count': '리뷰 수'},
                title=title,
                text='count',
                color_discrete_sequence=["#1f77b4"]
            )

            fig.update_layout(
                xaxis=dict(dtick=0.5),
                yaxis_title="리뷰 수",
                bargap=0.2
            )

            st.plotly_chart(fig, use_container_width=True)

            st.subheader(f"🔍 '{clicked_word}' 키워드가 포함된 리뷰 {len(filtered_df)}개")
            
            filtered_df = filtered_df[['star_rating', 'visit_date', 'review_text']].sort_values(by='star_rating')
            st.dataframe(filtered_df)

        else:
            filtered_df = df
            title = "전체 리뷰 별점 분포"

            # 2. value_counts() → dict → DataFrame로 처리
            rating_counts = (
                filtered_df['star_rating']
                .value_counts()
                .to_dict()
            )

            # 3. 누락된 별점 0으로 채우기
            rating_data = [{'star_rating': i, 'count': rating_counts.get(i, 0)} for i in [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]]
            rating_counts_df = pd.DataFrame(rating_data)

                    # Plotly 히스토그램
            fig = px.bar(
                rating_counts_df,
                x='star_rating',
                y='count',
                labels={'star_rating': '별점', 'count': '리뷰 수'},
                title=title,
                text='count',
                color_discrete_sequence=["#1f77b4"]
            )

            fig.update_layout(
                xaxis=dict(dtick=0.5),
                yaxis_title="리뷰 수",
                bargap=0.2
            )

            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()