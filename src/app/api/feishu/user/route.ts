import { NextRequest, NextResponse } from 'next/server';
import { getUserInfoByCode, getUserInfoByOpenId, getUserInfoByUserId } from '@/lib/feishu';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    
    // 方式1: 通过 code 换取用户信息（飞书 JSSDK 授权）
    const code = searchParams.get('code');
    
    if (code) {
      const userInfo = await getUserInfoByCode(code);
      if (userInfo) {
        return NextResponse.json({
          success: true,
          data: userInfo,
        });
      } else {
        return NextResponse.json(
          { error: '通过授权码获取用户信息失败' },
          { status: 401 }
        );
      }
    }

    // 方式2: 从 headers 获取（调试用）
    const openId = request.headers.get('x-feishu-open-id') || undefined;
    const userId = request.headers.get('x-feishu-user-id') || undefined;

    let userInfo = null;

    if (openId) {
      userInfo = await getUserInfoByOpenId(openId);
    } else if (userId) {
      userInfo = await getUserInfoByUserId(userId);
    }

    if (!userInfo) {
      return NextResponse.json(
        { error: '无法获取用户信息，请确保从飞书应用入口访问' },
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
