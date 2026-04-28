import { NextRequest, NextResponse } from 'next/server';
import { getPasswordByUserId } from '@/lib/db';
import { extractUserIdFromHeaders } from '@/lib/feishu';

export async function GET(request: NextRequest) {
  try {
    const { userId, openId } = extractUserIdFromHeaders(request.headers);
    
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
