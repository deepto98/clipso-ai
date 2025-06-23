import React, { useState, useEffect } from "react";
import { useLocation, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Download,
  Copy,
  Film,
  Edit,
  Cog,
  Settings,
  Share2,
  Twitter,
  Send,
} from "lucide-react";
import AppContainer from "@/components/layout/AppContainer";
import { useToast } from "@/hooks/use-toast";
import { Card } from "@/components/ui/card";
import PageHeading from "@/components/ui/page-heading";
import { getVideoByShareId, getFinalVideoByShareId } from "@/lib/api";

const PreviewPage = () => {
  const { toast } = useToast();
  const location = useLocation();
  const params = useParams();
  const locationState = location.state || {
    filename: null,
    finalVideoUrl: null,
  };

  // Get URL parameter if present, otherwise use location state
  const videoIdFromURL = params.videoId;
  const [filename, setFilename] = useState<string | null>(
    locationState.filename,
  );
  const [finalVideoUrl, setFinalVideoUrl] = useState<string | null>(
    locationState.finalVideoUrl,
  );

  const [captionsVisible, setCaptionsVisible] = useState(true);
  const [videoQuality, setVideoQuality] = useState("high");
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [isProcessedVideo, setIsProcessedVideo] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Get share_id from video info
  const [shareId, setShareId] = useState<string | null>(videoIdFromURL || null);

  // First effect: handle video ID from URL if present
  useEffect(() => {
    if (videoIdFromURL && !filename) {
      // If we have a video ID from URL but no filename, fetch the video data
      setIsLoading(true);

      // Use the new API function to get video by share_id
      getVideoByShareId(videoIdFromURL)
        .then((videoData) => {
          console.log("Found video by share_id:", videoData);
          // Set filename from the API response
          setFilename(videoData.filename);

          // Check if final video is available
          if (videoData.has_final_video && videoData.final_video_url) {
            setFinalVideoUrl(videoData.final_video_url);
          } else if (videoData.status === "rendering") {
            toast({
              title: "Processing in progress",
              description:
                "This video is still being processed. Please check back later.",
              variant: "default",
            });
          }
        })
        .catch((error) => {
          console.error("Error fetching video by share_id:", error);

          // Try legacy method as fallback
          console.log("Trying legacy method with videoId as filename...");

          // Convert videoId back to filename (add extension) - legacy fallback method
          const decodedVideoId = decodeURIComponent(videoIdFromURL);
          const filenameWithExt = `${decodedVideoId}.webm`;
          setFilename(filenameWithExt);

          // Fetch the final video URL from the backend using legacy approach
          fetch(`/api/final_video/${encodeURIComponent(filenameWithExt)}`)
            .then((response) => {
              if (!response.ok) throw new Error("Video not found");
              return response.json();
            })
            .then((data) => {
              if (data.status === "completed" && data.final_video_url) {
                setFinalVideoUrl(data.final_video_url);
              } else {
                toast({
                  title: "Processing in progress",
                  description:
                    "This video is still being processed. Please check back later.",
                  variant: "default",
                });
              }
            })
            .catch((err) => {
              console.error("Legacy approach also failed:", err);
              toast({
                title: "Video not found",
                description:
                  "The requested video could not be found or is still processing.",
                variant: "destructive",
              });
            });
        })
        .finally(() => {
          setIsLoading(false);
        });
    }
  }, [videoIdFromURL, toast]);

  // Second effect: load video when filename or finalVideoUrl change
  useEffect(() => {
    // If we received a final video URL, use that
    if (finalVideoUrl) {
      setVideoUrl(finalVideoUrl);
      setIsProcessedVideo(true);
      console.log("Using processed final video URL:", finalVideoUrl);
    } else if (filename) {
      // Otherwise, fall back to the original uploaded file
      const url = `/api/uploads/${encodeURIComponent(filename)}`;
      setVideoUrl(url);
      console.log("Using original video URL:", url);

      // Show a warning that we're using the original video
      toast({
        title: "Using original video",
        description:
          "The enhanced video is not available yet. Showing original video instead.",
        variant: "default",
      });
    } else if (!isLoading && !videoIdFromURL) {
      console.error("No filename provided");
      toast({
        title: "Error",
        description: "No video filename provided. Please upload a video first.",
        variant: "destructive",
      });
    }
  }, [filename, finalVideoUrl, toast, isLoading, videoIdFromURL]);

  const handleDownload = async () => {
    if (!videoUrl) {
      toast({
        title: "Error",
        description: "No video available to download.",
        variant: "destructive",
      });
      return;
    }

    // Get the appropriate download URL
    let downloadUrl = videoUrl;

    // Check if this is a direct Cloudflare URL or an API stream endpoint
    const isCloudflareUrl = videoUrl.includes(
      "pub-f7fdd9a323df414ba0d52f4474f6f12f.r2.dev",
    );

    // If this is a processed video with a Cloudflare URL, we'll create a direct download
    if (isProcessedVideo && isCloudflareUrl) {
      // Use share_id for streaming if available, otherwise use filename
      let idForDownload = shareId;
      if (!idForDownload && filename) {
        idForDownload = await getShareIdFromFilename(filename);
      }

      if (idForDownload) {
        // Use the stream_by_share_id endpoint
        downloadUrl = `/api/stream_by_share/${encodeURIComponent(idForDownload)}?download=true`;
      } else {
        // Fallback to legacy endpoint
        downloadUrl = `/api/stream_final_video/${encodeURIComponent(filename)}?download=true`;
      }
    }
    // For regular API URLs, ensure download parameter is set
    else if (videoUrl.startsWith("/api/")) {
      downloadUrl = videoUrl.includes("?")
        ? `${videoUrl}&download=true`
        : `${videoUrl}?download=true`;
    }

    // Create a link to trigger the download
    const a = document.createElement("a");
    a.href = downloadUrl;

    // Set the download attribute for browsers that support it
    // This forces a download instead of navigation
    if (!isProcessedVideo) {
      // For original videos, use original filename
      a.download = filename || "clipso-video.webm";
    } else {
      // For processed videos, use enhanced filename
      const outputFilename = `clipso_enhanced_${filename?.replace(/\.[^/.]+$/, "") || "video"}.mp4`;
      a.download = outputFilename;
    }

    // Append to the body, click, and remove
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    toast({
      title: "Download started",
      description: "Your video will be downloaded shortly.",
    });
  };

  // Function to get share_id if we don't have it yet
  // Remove duplicate declaration - using the state variable declared above
  const getShareIdFromFilename = async (videoFilename: string) => {
    try {
      // Make an API call to get video info including share_id
      const response = await fetch(
        `/api/uploads/${encodeURIComponent(videoFilename)}/info`,
      );
      if (response.ok) {
        const data = await response.json();
        console.log("Got video info with share_id:", data);
        if (data.share_id) {
          setShareId(data.share_id);
          return data.share_id;
        }
      }

      // Fallback - use filename-based method (legacy)
      console.log("Using legacy share method (filename-based)");
      const filenameNoExt = videoFilename.replace(/\.[^/.]+$/, "");
      return encodeURIComponent(filenameNoExt);
    } catch (error) {
      console.error("Failed to get share_id:", error);
      // Fallback - use filename-based method (legacy)
      const filenameNoExt = videoFilename.replace(/\.[^/.]+$/, "");
      return encodeURIComponent(filenameNoExt);
    }
  };

  const handleCopyLink = async () => {
    if (!filename) {
      toast({
        title: "Error",
        description: "No video available to share.",
        variant: "destructive",
      });
      return;
    }

    // Either use already set share_id or get one
    let idForSharing = shareId;
    if (!idForSharing) {
      idForSharing = await getShareIdFromFilename(filename);
    }

    const shareableLink = `${window.location.origin}/preview/${idForSharing}`;

    navigator.clipboard.writeText(shareableLink);
    toast({
      title: "Link copied",
      description: "Shareable link copied to clipboard",
    });
  };

  return (
    <AppContainer>
      <div className="flex flex-col items-center max-w-4xl mx-auto">
        <PageHeading
          title="Your Enhanced Video"
          description="Preview your video with AI-generated captions and B-roll footage"
          descriptionClassName="text-center"
        />

        {/* Video player section - centered */}
        <div className="w-full relative aspect-video bg-black rounded-lg overflow-hidden mb-6">
          {videoUrl ? (
            <video
              src={videoUrl}
              className="w-full h-full object-contain"
              controls
              autoPlay={false}
              playsInline
            >
              Your browser does not support the video tag.
            </video>
          ) : (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-white text-opacity-50 flex flex-col items-center">
                <Film className="h-16 w-16 mb-2" />
                <p>Loading video preview...</p>
              </div>
            </div>
          )}

          {/* Show an indicator if this is the processed video with B-roll and captions */}
          {isProcessedVideo && (
            <div className="absolute top-2 right-2 bg-green-500 text-white px-2 py-1 rounded-md text-xs font-medium">
              Enhanced Video
            </div>
          )}

          {/* Only show caption overlay if it's not a processed video (processed video already has captions) */}
          {/* {captionsVisible && !isProcessedVideo && (
            <div className="absolute bottom-8 left-0 right-0 flex justify-center">
              <div className="bg-black/70 text-white px-4 py-2 rounded-md text-center max-w-md">
                This is an example of how captions would appear in your video.
              </div>
            </div>
          )} */}
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap gap-4 mb-8 justify-center">
          <Button
            onClick={handleDownload}
            className="gap-2 bg-purple-600 hover:bg-purple-700"
          >
            <Download className="h-4 w-4" />
            Download Video
          </Button>

          <Button variant="outline" onClick={handleCopyLink} className="gap-2">
            <Copy className="h-4 w-4" />
            Copy Link
          </Button>
        </div>

        {/* Social Share Section */}
        <div className="w-full md:max-w-2xl mx-auto mb-6">
          <Card className="p-4">
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-medium mb-3 flex items-center gap-2">
                  <Share2 className="h-5 w-5 text-purple-600" />
                  Share Your Video
                </h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Share your enhanced video with friends and followers
                </p>

                <div className="grid grid-cols-2 gap-3">
                  <Button
                    variant="outline"
                    className="flex items-center justify-center gap-2 p-6 h-auto"
                    onClick={async () => {
                      if (!filename) return;

                      // Get share_id for sharing
                      let idForSharing = shareId;
                      if (!idForSharing) {
                        idForSharing = await getShareIdFromFilename(filename);
                      }

                      const shareableLink = `${window.location.origin}/preview/${idForSharing}`;

                      // Create WhatsApp sharing URL
                      const whatsappText = encodeURIComponent(
                        `Check this video made on Clipso\n${shareableLink}`,
                      );
                      const whatsappUrl = `https://wa.me/?text=${whatsappText}`;

                      // Open in new window
                      window.open(whatsappUrl, "_blank");
                    }}
                  >
                    <Send className="h-6 w-6 text-green-600" />
                    <div className="flex flex-col items-start">
                      <span className="font-medium">WhatsApp</span>
                      <span className="text-xs text-muted-foreground">
                        Share with friends
                      </span>
                    </div>
                  </Button>

                  <Button
                    variant="outline"
                    className="flex items-center justify-center gap-2 p-6 h-auto"
                    onClick={async () => {
                      if (!filename) return;

                      // Get share_id for sharing
                      let idForSharing = shareId;
                      if (!idForSharing) {
                        idForSharing = await getShareIdFromFilename(filename);
                      }

                      const shareableLink = `${window.location.origin}/preview/${idForSharing}`;

                      // Create Twitter sharing URL
                      const twitterText = encodeURIComponent(
                        `Check this video made on Clipso`,
                      );
                      const twitterUrl = `https://twitter.com/intent/tweet?text=${twitterText}&url=${encodeURIComponent(shareableLink)}`;

                      // Open in new window
                      window.open(twitterUrl, "_blank");
                    }}
                  >
                    <Twitter className="h-6 w-6 text-blue-500" />
                    <div className="flex flex-col items-start">
                      <span className="font-medium">Twitter</span>
                      <span className="text-xs text-muted-foreground">
                        Tweet your video
                      </span>
                    </div>
                  </Button>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </AppContainer>
  );
};

export default PreviewPage;
