#!/bin/bash
sed -i '199s|// Navigate to preview|// Generate a videoId for the shareable URL\n                    const videoId = encodeURIComponent(filename.replace(/\\.[^/.]+$/, "")); // Remove file extension\n                    \n                    // Navigate to preview with shareable URL|' frontend/src/pages/Processing.tsx
sed -i '199s|navigate.*/preview.|navigate(`/preview/${videoId}`|' frontend/src/pages/Processing.tsx

sed -i '221s|// Navigate to preview with the final video data|// Generate a videoId for the shareable URL\n                    const videoId = encodeURIComponent(filename.replace(/\\.[^/.]+$/, "")); // Remove file extension\n                    \n                    // Navigate to shareable preview URL with the final video data|' frontend/src/pages/Processing.tsx
sed -i '221s|navigate.*/preview.|navigate(`/preview/${videoId}`|' frontend/src/pages/Processing.tsx

sed -i '267s|// Navigate to preview after delay|// Generate a videoId for the shareable URL\n                  const videoId = encodeURIComponent(filename.replace(/\\.[^/.]+$/, "")); // Remove file extension\n                  \n                  // Navigate to preview after delay with shareable URL|' frontend/src/pages/Processing.tsx
sed -i '267s|navigate.*/preview.|navigate(`/preview/${videoId}`|' frontend/src/pages/Processing.tsx

sed -i '319s|// Navigate to preview|// Generate a videoId for the shareable URL\n                    const videoId = encodeURIComponent(filename.replace(/\\.[^/.]+$/, "")); // Remove file extension\n                    \n                    // Navigate to preview with shareable URL|' frontend/src/pages/Processing.tsx
sed -i '319s|navigate.*/preview.|navigate(`/preview/${videoId}`|' frontend/src/pages/Processing.tsx

sed -i '341s|// Navigate to preview with the final video data|// Generate a videoId for the shareable URL\n                    const videoId = encodeURIComponent(filename.replace(/\\.[^/.]+$/, "")); // Remove file extension\n                    \n                    // Navigate to shareable preview URL with the final video data|' frontend/src/pages/Processing.tsx
sed -i '341s|navigate.*/preview.|navigate(`/preview/${videoId}`|' frontend/src/pages/Processing.tsx

sed -i '387s|// Navigate to preview after delay|// Generate a videoId for the shareable URL\n                  const videoId = encodeURIComponent(filename.replace(/\\.[^/.]+$/, "")); // Remove file extension\n                  \n                  // Navigate to preview after delay with shareable URL|' frontend/src/pages/Processing.tsx
sed -i '387s|navigate.*/preview.|navigate(`/preview/${videoId}`|' frontend/src/pages/Processing.tsx
