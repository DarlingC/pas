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
