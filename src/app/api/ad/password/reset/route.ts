import { NextRequest, NextResponse } from 'next/server';
import { resetAdPassword } from '@/lib/ad';
import { savePassword } from '@/lib/db';
import { getUserInfoByOpenId, getUserInfoByUserId, extractUserIdFromHeaders } from '@/lib/feishu';

export async function POST(request: NextRequest) {
  try {
    const { userId, openId } = extractUserIdFromHeaders(request.headers);
    
    let feishuUserId = userId || openId;
    
    if (!feishuUserId) {
      return NextResponse.json(
        { error: '无法识别用户身份' },
        { status: 400 }
      );
    }

    const body = await request.json();
    const { newPassword, confirmPassword } = body;

    if (!newPassword || !confirmPassword) {
      return NextResponse.json(
        { error: '请填写新密码和确认密码' },
        { status: 400 }
      );
    }

    if (newPassword !== confirmPassword) {
      return NextResponse.json(
        { error: '两次输入的密码不一致' },
        { status: 400 }
      );
    }

    if (newPassword.length < 8) {
      return NextResponse.json(
        { error: '密码长度不能少于8位' },
        { status: 400 }
      );
    }

    let userName: string | null = null;
    if (openId) {
      const userInfo = await getUserInfoByOpenId(openId);
      userName = userInfo?.name || null;
    } else if (userId) {
      const userInfo = await getUserInfoByUserId(userId);
      userName = userInfo?.name || null;
    }

    const adResult = await resetAdPassword(feishuUserId, newPassword);

    if (!adResult.success) {
      return NextResponse.json(
        { error: adResult.message },
        { status: 500 }
      );
    }

    savePassword(feishuUserId, userName, newPassword);

    return NextResponse.json({
      success: true,
      message: '密码重置成功',
    });
  } catch (error) {
    console.error('密码重置错误:', error);
    return NextResponse.json(
      { error: '密码重置失败' },
      { status: 500 }
    );
  }
}
