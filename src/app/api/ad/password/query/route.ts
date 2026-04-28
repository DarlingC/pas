import { NextRequest, NextResponse } from 'next/server';
import { getPasswordByUserId } from '@/lib/db';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    
    // 优先从 URL 参数获取
    const openId = searchParams.get('open_id') || undefined;
    const userId = searchParams.get('user_id') || undefined;

    let feishuUserId = userId || openId;

    if (!feishuUserId) {
      return NextResponse.json(
        { error: '无法识别用户身份' },
        { status: 400 }
      );
    }

    const record = getPasswordByUserId(feishuUserId);

    if (!record) {
      return NextResponse.json({
        success: false,
        message: '未找到已存储的密码',
        data: null,
      });
    }

    return NextResponse.json({
      success: true,
      data: {
        password: record.password,
        updatedAt: record.updated_at,
      },
    });
  } catch (error) {
    console.error('密码查询错误:', error);
    return NextResponse.json(
      { error: '密码查询失败' },
      { status: 500 }
    );
  }
}
