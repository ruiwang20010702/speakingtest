/**
 * 浏览器环境检测工具
 */

/**
 * 检测是否是微信内置浏览器
 */
export function isWechat(): boolean {
  return /micromessenger/i.test(navigator.userAgent);
}

/**
 * 检测是否是企业微信
 */
export function isWxWork(): boolean {
  return /wxwork/i.test(navigator.userAgent);
}

/**
 * 检测是否是钉钉
 */
export function isDingTalk(): boolean {
  return /dingtalk/i.test(navigator.userAgent);
}

/**
 * 检测是否是 Android 系统
 */
export function isAndroid(): boolean {
  return /android/i.test(navigator.userAgent);
}

/**
 * 检测是否是 iOS 系统
 */
export function isIOS(): boolean {
  return /iphone|ipad|ipod/i.test(navigator.userAgent);
}

/**
 * 检测是否是移动端
 */
export function isMobile(): boolean {
  return isAndroid() || isIOS();
}

/**
 * 检测是否需要显示微信跳转引导
 * 只拦截 Android 微信（iOS 微信对麦克风支持较好）
 */
export function shouldShowWechatGuide(): boolean {
  return isWechat() && isAndroid();
}

/**
 * 检测是否是任意 App 内置浏览器（微信/企微/钉钉）
 */
export function isInAppBrowser(): boolean {
  return isWechat() || isWxWork() || isDingTalk();
}
