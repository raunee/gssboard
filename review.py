import streamlit as st
import streamlit_wordcloud as wordcloud
import pandas as pd
import plotly.express as px
import uuid

# 캐시된 데이터 로드
@st.cache_data
def load_processed_data():
    df = pd.read_pickle('data/processed_reviews.pkl')
    words = pd.read_pickle('data/wordcloud_data.pkl').to_dict('records')
    return df, words

def main():

    st.title("🎨 전시 리뷰 워드클라우드")
    
    # 데이터 로드
    df, words = load_processed_data()

    if "clicked_word" not in st.session_state:
        st.session_state.clicked_word = None
    if "wordcloud_reset" not in st.session_state:
        st.session_state.wordcloud_reset = False

    # 초기화 버튼
    if st.session_state.clicked_word:
        if st.button("🔄 선택된 키워드 초기화"):
            st.session_state.clicked_word = None
            st.session_state.wordcloud_reset = True
            st.rerun()
    
    # ✅ key: 초기화 트리거가 있으면 랜덤 키 사용
    if st.session_state.wordcloud_reset:
        wordcloud_key = f"wordcloud_{uuid.uuid4()}"
        st.session_state.wordcloud_reset = False  # 딱 한 번만 리셋되도록!
    else:
        wordcloud_key = "wordcloud"

    selected_word = wordcloud.visualize(
        words,
        per_word_coloring=True,
        tooltip_data_fields={
            'text': '키워드',
            'value': '빈도',
            'avg_rating': '평균 별점'
        },
        width="100%",
        height="500px",
        key=wordcloud_key
    )

    # 워드클라우드 시각화
    
    if (
        selected_word
        and isinstance(selected_word.get("clicked"), dict)
    ):
        st.session_state.clicked_word = selected_word["clicked"]["text"]
    
    # 클릭된 키워드가 있으면 리뷰 출력
    if st.session_state.clicked_word:
        filtered_df = df[df['keywords'].apply(lambda x: isinstance(x, list) and st.session_state.clicked_word in x)]
        title = f"'{st.session_state.clicked_word}' 키워드가 포함된 리뷰 별점 분포"

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

        st.subheader(f"🔍 '{st.session_state.clicked_word}' 키워드가 포함된 리뷰 {len(filtered_df)}개")
        
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