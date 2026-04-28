import { NextRequest, NextResponse } from 'next/server';
import { getUserInfoByOpenId, getUserInfoByUserId, extractUserIdFromHeaders } from '@/lib/feishu';

export async function GET(request: NextRequest) {
  try {
    const { userId, openId } = extractUserIdFromHeaders(request.headers);

    let userInfo = null;

    if (openId) {
      userInfo = await getUserInfoByOpenId(openId);
    } else if (userId) {
      userInfo = await getUserInfoByUserId(userId);
    }

    if (!userInfo) {
      return NextResponse.json(
        { error: '无法获取用户信息，请确认应用已配置正确的权限' },
        { status: 401 }
      );
    }

    return NextResponse.json({
      success: true,
      data: userInfo,
    });
  } catch (error) {
    console.error('获取用户信息错误:', error);
    return NextResponse.json(
      { error: '获取用户信息失败' },
      { status: 500 }
    );
  }
}
