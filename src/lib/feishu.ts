import * as lark from '@larksuiteoapi/node-sdk';

const FEISHU_APP_ID = process.env.FEISHU_APP_ID || '';
const FEISHU_APP_SECRET = process.env.FEISHU_APP_SECRET || '';

export interface FeishuUserInfo {
  user_id: string;
  name: string;
  en_name?: string;
  email?: string;
  avatar?: {
    avatar_72?: string;
    avatar_240?: string;
  };
}

export function getFeishuClient(): lark.Client {
  return new lark.Client({
    appId: FEISHU_APP_ID,
    appSecret: FEISHU_APP_SECRET,
    disableTokenCache: false,
  });
}

// 获取 app_access_token
async function getAppAccessToken(): Promise<string | null> {
  try {
    const response = await fetch('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        app_id: FEISHU_APP_ID,
        app_secret: FEISHU_APP_SECRET,
      }),
    });
    
    const data = await response.json();
    if (data.code === 0) {
      return data.tenant_access_token;
    }
    return null;
  } catch (error) {
    console.error('获取 app_access_token 失败:', error);
    return null;
  }
}

// 通过 code 换取用户信息（飞书 JSSDK 授权流程）
export async function getUserInfoByCode(code: string): Promise<FeishuUserInfo | null> {
  try {
    // 获取 app_access_token
    const appAccessToken = await getAppAccessToken();
    if (!appAccessToken) {
      console.error('无法获取 app_access_token');
      return null;
    }

    // 用 code 换取 user_access_token
    const tokenResponse = await fetch('https://open.feishu.cn/open-apis/authen/v1/oidc/access_token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${appAccessToken}`,
      },
      body: JSON.stringify({
        grant_type: 'authorization_code',
        code: code,
      }),
    });

    const tokenData = await tokenResponse.json();
    console.log('tokenData:', JSON.stringify(tokenData));
    
    if (tokenData.code !== 0) {
      console.error('换取 user_access_token 失败:', tokenData.msg);
      return null;
    }

    const userAccessToken = tokenData.data?.access_token;
    if (!userAccessToken) {
      console.error('未获取到 user_access_token');
      return null;
    }

    // 用 user_access_token 获取用户信息
    const userResponse = await fetch('https://open.feishu.cn/open-apis/authen/v1/user_info', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${userAccessToken}`,
      },
    });

    const userData = await userResponse.json();
    console.log('userData:', JSON.stringify(userData));

    if (userData.code === 0 && userData.data) {
      const user = userData.data;
      return {
        user_id: user.open_id || user.user_id || '',
        name: user.name || '',
        en_name: user.en_name,
        email: user.email,
      };
    }

    return null;
  } catch (error) {
    console.error('通过 code 获取用户信息失败:', error);
    return null;
  }
}

export async function getUserInfoByOpenId(openId: string): Promise<FeishuUserInfo | null> {
  try {
    const client = getFeishuClient();
    const response = await client.request({
      method: 'GET',
      url: '/contact/v3/users/:user_id',
      params: {
        user_id: openId,
        user_id_type: 'open_id',
      },
    });
    
    if (response.code === 0 && response.data?.user) {
      const user = response.data.user;
      return {
        user_id: user.open_id || user.user_id || '',
        name: user.name || '',
        en_name: user.en_name,
        email: user.email,
        avatar: user.avatar,
      };
    }
    return null;
  } catch (error) {
    console.error('获取飞书用户信息失败:', error);
    return null;
  }
}

export async function getUserInfoByUserId(userId: string): Promise<FeishuUserInfo | null> {
  try {
    const client = getFeishuClient();
    const response = await client.request({
      method: 'GET',
      url: '/contact/v3/users/:user_id',
      params: {
        user_id: userId,
        user_id_type: 'user_id',
      },
    });
    
    if (response.code === 0 && response.data?.user) {
      const user = response.data.user;
      return {
        user_id: user.user_id || '',
        name: user.name || '',
        en_name: user.en_name,
        email: user.email,
        avatar: user.avatar,
      };
    }
    return null;
  } catch (error) {
    console.error('获取飞书用户信息失败:', error);
    return null;
  }
}

export function extractUserIdFromHeaders(headers: Headers): { userId?: string; openId?: string } {
  const userId = headers.get('x-feishu-user-id') || undefined;
  const openId = headers.get('x-feishu-open-id') || undefined;
  return { userId, openId };
}
