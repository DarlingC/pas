'use client';

import Script from 'next/script';

export default function FeishuJSSDK() {
  return (
    <Script
      src="https://lf1-cdn-tos.bytegoofy.com/goofy/lark/op/h5-js-sdk-1.5.26.js"
      strategy="afterInteractive"
      onLoad={() => {
        console.log('飞书 JSSDK 加载成功');
      }}
      onError={() => {
        console.error('飞书 JSSDK 加载失败');
      }}
    />
  );
}
