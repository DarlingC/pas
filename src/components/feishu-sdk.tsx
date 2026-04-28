'use client';

import { useEffect } from 'react';

export default function FeishuJSSDK() {
  useEffect(() => {
    // 动态加载飞书 JSSDK
    const script = document.createElement('script');
    script.src = 'https://lf1-cdn-tos.bytegoofy.com/goofy/lark/op/h5-js-sdk-1.5.26.js';
    script.async = true;
    script.onload = () => {
      console.log('飞书 JSSDK 加载完成');
      console.log('window.h5sdk:', (window as any).h5sdk);
      console.log('window.tt:', (window as any).tt);
    };
    script.onerror = () => {
      console.error('飞书 JSSDK 加载失败');
    };
    document.body.appendChild(script);
  }, []);

  return null;
}
