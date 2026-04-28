'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Eye, EyeOff, Copy, Check, KeyRound, Search } from 'lucide-react';

interface UserInfo {
  user_id: string;
  name: string;
  en_name?: string;
}

export default function HomePage() {
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  const [resetMessage, setResetMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const [queryLoading, setQueryLoading] = useState(false);
  const [queryResult, setQueryResult] = useState<{ password: string; updatedAt: string } | null>(null);
  const [showQueryPassword, setShowQueryPassword] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchUserInfo();
  }, []);

  async function fetchUserInfo() {
    try {
      // 从 URL 参数获取飞书用户信息
      const params = new URLSearchParams(window.location.search);
      const openId = params.get('open_id') || params.get('openId');
      const userId = params.get('user_id') || params.get('userId');
      
      // 构建查询参数
      const queryParams = new URLSearchParams();
      if (openId) queryParams.set('open_id', openId);
      if (userId) queryParams.set('user_id', userId);

      const queryString = queryParams.toString();
      const url = queryString ? `/api/feishu/user?${queryString}` : '/api/feishu/user';

      const response = await fetch(url);
      const data = await response.json();
      if (data.success) {
        setUserInfo(data.data);
      } else {
        setError(data.error || '获取用户信息失败');
      }
    } catch (err) {
      setError('无法连接到服务器');
    } finally {
      setLoading(false);
    }
  }

  async function handleResetPassword(e: React.FormEvent) {
    e.preventDefault();
    setResetMessage(null);

    if (!newPassword || !confirmPassword) {
      setResetMessage({ type: 'error', text: '请填写所有字段' });
      return;
    }

    if (newPassword !== confirmPassword) {
      setResetMessage({ type: 'error', text: '两次输入的密码不一致' });
      return;
    }

    if (newPassword.length < 8) {
      setResetMessage({ type: 'error', text: '密码长度不能少于8位' });
      return;
    }

    setResetLoading(true);
    try {
      const params = new URLSearchParams(window.location.search);
      const openId = params.get('open_id') || params.get('openId');
      const userId = params.get('user_id') || params.get('userId');

      const response = await fetch('/api/ad/password/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          newPassword, 
          confirmPassword,
          open_id: openId,
          user_id: userId
        }),
      });
      const data = await response.json();
      if (data.success) {
        setResetMessage({ type: 'success', text: '密码重置成功' });
        setNewPassword('');
        setConfirmPassword('');
      } else {
        setResetMessage({ type: 'error', text: data.error || '密码重置失败' });
      }
    } catch (err) {
      setResetMessage({ type: 'error', text: '请求失败，请稍后重试' });
    } finally {
      setResetLoading(false);
    }
  }

  async function handleQueryPassword() {
    setQueryLoading(true);
    setQueryResult(null);
    setShowQueryPassword(false);
    try {
      const params = new URLSearchParams(window.location.search);
      const openId = params.get('open_id') || params.get('openId');
      const userId = params.get('user_id') || params.get('userId');

      const queryParams = new URLSearchParams();
      if (openId) queryParams.set('open_id', openId);
      if (userId) queryParams.set('user_id', userId);

      const queryString = queryParams.toString();
      const url = queryString ? `/api/ad/password/query?${queryString}` : '/api/ad/password/query';

      const response = await fetch(url);
      const data = await response.json();
      if (data.success && data.data) {
        setQueryResult(data.data);
      } else {
        setQueryResult(null);
        alert(data.error || '未找到已存储的密码');
      }
    } catch (err) {
      alert('查询失败，请稍后重试');
    } finally {
      setQueryLoading(false);
    }
  }

  function handleCopy() {
    if (queryResult?.password) {
      navigator.clipboard.writeText(queryResult.password);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-red-600">错误</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-500">
              请确保从飞书应用入口访问此页面，并确认应用已配置正确的权限。
            </p>
            <p className="text-xs text-gray-400 mt-4">
              当前URL: {typeof window !== 'undefined' ? window.location.href : ''}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-900">AD 密码管理</h1>
          <p className="text-gray-600 mt-2">
            欢迎，{userInfo?.name || userInfo?.en_name || '用户'}
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5" />
              重置密码
            </CardTitle>
            <CardDescription>
              输入新密码并确认，密码将同步更新到 AD 域
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleResetPassword} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="newPassword">新密码</Label>
                <div className="relative">
                  <Input
                    id="newPassword"
                    type={showPassword ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="请输入新密码（至少8位）"
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">确认密码</Label>
                <div className="relative">
                  <Input
                    id="confirmPassword"
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="请再次输入新密码"
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {resetMessage && (
                <Alert variant={resetMessage.type === 'error' ? 'destructive' : 'default'}>
                  <AlertDescription>{resetMessage.text}</AlertDescription>
                </Alert>
              )}

              <Button type="submit" className="w-full" disabled={resetLoading}>
                {resetLoading ? '处理中...' : '重置密码'}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5" />
              查询密码
            </CardTitle>
            <CardDescription>
              查询您已存储的 AD 密码
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              onClick={handleQueryPassword}
              variant="outline"
              className="w-full"
              disabled={queryLoading}
            >
              {queryLoading ? '查询中...' : '查询密码'}
            </Button>

            {queryResult && (
              <div className="space-y-3">
                <div className="space-y-2">
                  <Label>已存储的密码</Label>
                  <div className="flex gap-2">
                    <Input
                      type={showQueryPassword ? 'text' : 'password'}
                      value={queryResult.password}
                      readOnly
                      className="flex-1"
                    />
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => setShowQueryPassword(!showQueryPassword)}
                    >
                      {showQueryPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={handleCopy}
                      className={copied ? 'bg-green-50 text-green-600' : ''}
                    >
                      {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
                <p className="text-xs text-gray-500">
                  最后更新时间：{new Date(queryResult.updatedAt).toLocaleString('zh-CN')}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
