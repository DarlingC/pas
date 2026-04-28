import { NextResponse } from 'next/server';
import { getDb } from '@/lib/db';

export async function GET() {
  try {
    const db = getDb();
    db.prepare('SELECT 1').get();
    return NextResponse.json({
      success: true,
      message: '数据库连接正常',
    });
  } catch (error) {
    console.error('数据库初始化检查错误:', error);
    return NextResponse.json(
      { error: '数据库初始化失败' },
      { status: 500 }
    );
  }
}
