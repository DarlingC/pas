import { NextResponse } from 'next/server';

const FEISHU_APP_ID = process.env.FEISHU_APP_ID || '';

export async function GET() {
  if (!FEISHU_APP_ID) {
    return NextResponse.json(
      { error: '未配置飞书应用ID' },
      { status: 500 }
    );
  }

  return NextResponse.json({
    appid: FEISHU_APP_ID,
  });
}
