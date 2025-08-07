"""
Simple FastAPI hello world application for testing with Dagger.
Follows SIMPLICITY and RELIABILITY principles.
"""
import uvicorn
from fastapi import FastAPI

app = FastAPI(title="Hello World API", version="1.0.0")


@app.get("/")
async def root():
    """Simple root endpoint returning hello world."""
    return {"message": "Hello, World!"}


@app.get("/health")
async def health_check():
    """Health check endpoint for service monitoring."""
    return {"status": "healthy", "service": "hello-world"}


if __name__ == "__main__":
    # Run the app when called as a module
    uvicorn.run(app, host="0.0.0.0", port=8000)
