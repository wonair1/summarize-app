# Makefile
client:
	streamlit run frontend/frontend.py --server.address=0.0.0.0 --server.port=8501 &
server:
	uvicorn backend.backend:app --host 0.0.0.0 --port 8000 &
