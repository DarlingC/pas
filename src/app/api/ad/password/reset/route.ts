import { NextRequest, NextResponse } from 'next/server';
import { resetAdPassword } from '@/lib/ad';
import { savePassword } from '@/lib/db';
import { getUserInfoByOpenId, getUserInfoByUserId } from '@/lib/feishu';

export async function POST(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    
    // 从 URL 参数获取
    let openId = searchParams.get('open_id') || undefined;
    let userId = searchParams.get('user_id') || undefined;
    
    const body = await request.json();
    const { newPassword, confirmPassword, open_id, user_id } = body;

    // 请求体中的参数优先级更高
    if (open_id) openId = open_id;
    if (user_id) userId = user_id;

    let feishuUserId = userId || openId;

    if (!feishuUserId) {
      return NextResponse.json(
        { error: '无法识别用户身份' },
        { status: 400 }
      );
    }

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
