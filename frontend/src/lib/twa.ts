import WebApp from "@twa-dev/sdk";

export const isTWA = () => {
  return !!WebApp.initData;
};

export const expandWebApp = () => {
  if (isTWA()) {
    WebApp.expand();
  }
};

export const setHeaderColor = (color: string) => {
  if (isTWA()) {
    WebApp.setHeaderColor(color as any);
  }
};

export const showMainButton = (text: string, onClick: () => void) => {
  if (isTWA()) {
    WebApp.MainButton.setText(text);
    WebApp.MainButton.onClick(onClick);
    WebApp.MainButton.show();
  }
};

export const hideMainButton = () => {
  if (isTWA()) {
    WebApp.MainButton.hide();
  }
};

export const hapticImpact = (style: "light" | "medium" | "heavy" | "rigid" | "soft" = "medium") => {
  if (isTWA()) {
    WebApp.HapticFeedback.impactOccurred(style);
  }
};

export const hapticNotification = (type: "error" | "success" | "warning") => {
  if (isTWA()) {
    WebApp.HapticFeedback.notificationOccurred(type);
  }
};

export const shareToTelegram = (text: string, url?: string) => {
  const shareUrl = url || window.location.href;
  const tgUrl = `https://t.me/share/url?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(text)}`;
  if (isTWA()) {
    WebApp.openTelegramLink(tgUrl);
  } else {
    window.open(tgUrl, "_blank");
  }
};
