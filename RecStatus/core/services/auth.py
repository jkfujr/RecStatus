import jwt
from typing import Optional, Dict
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta

from core.logs import log
from core.dependencies import get_config, get_auth

logger = log()

class Auth:
    """认证"""    
    def __init__(self, config):
        self.reload(config)

    def reload(self, config):
        """重新加载认证配置"""
        auth_config = config.get("AUTH", {})
        self.enabled = auth_config.get("ENABLE", False)
        self.secret_key = auth_config.get("AUTH_KEY", "114514")
        self.token_expire_minutes = auth_config.get("AUTH_KEY_EXPIRE", 60 * 24)
        self.users = {}
        
        user_configs = auth_config.get("AUTH_USER", {}) or {}
        
        if not isinstance(user_configs, dict):
            logger.warning("[Auth] AUTH_USER 配置无效，使用空字典")
            user_configs = {}
            
        for username, user_data in user_configs.items():
            if not isinstance(user_data, dict):
                logger.warning(f"[Auth] 用户 {username} 的配置无效，已跳过")
                continue
                
            actual_username = user_data.get("USER", username)
            password = user_data.get("PASS", "")
            if password:
                self.users[actual_username] = password
        
        logger.info(f"[Auth] 已加载 {len(self.users)} 个用户账号")
        logger.debug(f"[Auth] 认证已{'启用' if self.enabled else '禁用'}")
    
    def authenticate_user(self, username: str, password: str) -> bool:
        """验证用户名和密码"""
        if not self.enabled:
            return False
            
        return username in self.users and self.users[username] == password
    
    def create_token(self, username: str) -> str:
        """创建 token"""
        expire = datetime.utcnow() + timedelta(minutes=self.token_expire_minutes)
        token_data = {
            "sub": username,
            "exp": expire
        }
        return jwt.encode(token_data, self.secret_key, algorithm="HS256")
    
    def verify_token(self, token: str) -> Optional[str]:
        """验证 token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload.get("sub")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token已过期")
        except jwt.exceptions.DecodeError:
            raise HTTPException(status_code=401, detail="无效的Token")
        except Exception as e:
            logger.error(f"Token验证失败: {str(e)}")
            raise HTTPException(status_code=401, detail=f"Token验证失败: {str(e)}")
        
auth_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(auth_scheme),
    config: Dict = Depends(get_config), 
    auth_service: Auth = Depends(get_auth) # This needs Auth class itself
) -> str:
    """
    验证用户凭据并返回用户名。
    如果认证未启用，返回 'anonymous'。
    如果认证已启用但凭据无效或缺失，则引发 HTTPException。
    """
    # This function relies on the Auth class being available in this scope, which is correct.
    # It also depends on get_config and get_auth from dependencies.py, which is fine.
    if not config.get("AUTH", {}).get("ENABLE", False):
        return "anonymous"
    
    if not credentials:
        raise HTTPException(
            status_code=401, 
            detail="认证头缺失",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not auth_service:
        logger.error("[Auth] 依赖注入的 auth_service 为空")
        raise HTTPException(status_code=500, detail="认证服务不可用")
        
    username = auth_service.verify_token(credentials.credentials)
    if not username:
        raise HTTPException(
            status_code=401, 
            detail="无效的 Token 或认证失败",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username 
