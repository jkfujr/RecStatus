import sys, uvicorn
from typing import Dict
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from contextlib import asynccontextmanager

from core.logs import log, log_print
from core.services.auth import Auth
from core.services.cookie_manager import CookieManager
from core.config_manager import load_config
from core.dependencies import setup_dependencies, get_logger

from core.routers import room as room_router
from core.routers import server as server_router
from core.routers import auth as auth_router

# === 全局变量 ===
_config: Dict = None
_auth: Auth = None
_cookie_manager: CookieManager = None
_logger = None 

# === 生命周期 ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _config, _auth, _cookie_manager, _logger
    try:
        _logger = log()
        _config = load_config()
        _auth = Auth(_config)
        _logger.debug("[启动] 配置加载成功")
        _cookie_manager = CookieManager(_config)
        await _cookie_manager.start()
        _logger.debug("[启动] Cookie 管理器已启动")
        setup_dependencies(_config, _logger, _auth, _cookie_manager)
        _logger.debug("[启动] 依赖注入设置完成")
        
    except Exception as e:
        if _logger:
            _logger.error(f"[启动] 失败: {e}", exc_info=True)
        else:
            log_print(f"[启动] 失败 (logger 未初始化): {e}", "ERROR")
        if not _config:
            raise RuntimeError(f"配置加载失败，无法启动服务: {e}") from e
        sys.exit(1)

    yield # 应用运行

    # --- 关闭清理 --- 
    _logger.debug("[关闭] 应用正在关闭")
    if _cookie_manager:
        try:
            await _cookie_manager.stop()
            _logger.debug("[关闭] Cookie 管理器已停止")
        except Exception as e:
             _logger.error(f"[关闭] Cookie 管理器停止时出错: {e}", exc_info=True)
    _logger.debug("[关闭] 清理完成")

# === FastAPI 应用实例 ===
app = FastAPI(lifespan=lifespan, title="REC-Status API")

# --- 中间件 --- 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 包含 API Routers --- 
# 注 prefix 会添加到 router 中定义的所有路径之前
app.include_router(room_router.router, prefix="/api", tags=["Room Management"])
app.include_router(server_router.router, prefix="/api", tags=["Server Management"])
app.include_router(auth_router.router, prefix="/api", tags=["Authentication"])

# --- 静态文件和 SPA --- 
app.mount("/assets", StaticFiles(directory="web/assets"), name="assets")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon_ico():
    try:
        return FileResponse("web/favicon.ico")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="favicon.ico not found")

@app.get("/favicon.svg", include_in_schema=False)
async def favicon_svg():
    try:
        return FileResponse("web/favicon.svg")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="favicon.svg not found")

# SPA
@app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
async def serve_spa(full_path: str, logger = Depends(get_logger)):
    index_path = "web/index.html"
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
         logger.error(f"[前端] SPA 入口文件 {index_path} 未找到")
         raise HTTPException(status_code=404, detail=f"Frontend entry point not found at {index_path}")
    except Exception as e:
        logger.error(f"[前端] 加载 SPA 页面 {index_path} 失败: {e}")
        return HTMLResponse(content=f"<html><body><h1>500 - Internal Server Error</h1><p>Failed to load frontend application.</p></body></html>", status_code=500)


# === 入口 ===
if __name__ == "__main__":
    try:
        startup_config = load_config() 
        host = startup_config.get("HOST", "127.0.0.1")
        port = startup_config.get("PORT", 8080)
        temp_logger = log()
    except Exception as e:
        log_print(f"启动前初始化失败: {e}", "CRITICAL")
        sys.exit(1)
        
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level="info",
        reload=False
    )