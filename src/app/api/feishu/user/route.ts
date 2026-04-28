import { NextRequest, NextResponse } from 'next/server';
import { getUserInfoByOpenId, getUserInfoByUserId } from '@/lib/feishu';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    
    // 优先从 URL 参数获取，其次从 headers 获取
    const openId = searchParams.get('open_id') || request.headers.get('x-feishu-open-id') || undefined;
    const userId = searchParams.get('user_id') || request.headers.get('x-feishu-user-id') || undefined;

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
