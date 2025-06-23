import React, { useRef, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Video, VideoIcon, Square, Pause, Circle, Maximize } from "lucide-react";
import AppContainer from "@/components/layout/AppContainer";
import { useToast } from "@/hooks/use-toast";
import { uploadRecordedVideo } from "@/lib/api";

// Define aspect ratio presets
type AspectRatioPreset = {
  name: string;
  ratio: number;
  cssClass: string;
  description: string;
  value: number; // Adding value property for direct access in constraints
};

const ASPECT_RATIO_PRESETS: AspectRatioPreset[] = [
  {
    name: "Portrait (9:16)",
    ratio: 9/16,
    cssClass: "aspect-[9/16]",
    description: "Instagram Reels / TikTok",
    value: 9/16,
  },
  {
    name: "Square (1:1)",
    ratio: 1,
    cssClass: "aspect-square",
    description: "Instagram Posts",
    value: 1,
  },
  {
    name: "Landscape (16:9)",
    ratio: 16/9,
    cssClass: "aspect-[16/9]",
    description: "YouTube / Standard Video",
    value: 16/9,
  },
];

const RecordPage = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [countdown, setCountdown] = useState(0);
  const [recordingTime, setRecordingTime] = useState(0);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedAspectRatio, setSelectedAspectRatio] = useState<AspectRatioPreset>(ASPECT_RATIO_PRESETS[0]);
  // Start with a lower zoom value for less tight framing (0.7 is a bit zoomed out from the default)
  const [cameraZoom, setCameraZoom] = useState(0.7);
  // State to track when camera is being adjusted
  const [isAdjustingCamera, setIsAdjustingCamera] = useState(false);
  const navigate = useNavigate();
  const { toast } = useToast();

  const setupCamera = async (aspectRatioValue: number = 9/16) => {
    try {
      // Show loading indicator while camera is being adjusted
      setIsAdjustingCamera(true);
      
      // Get the new media stream first before stopping the old one
      // This avoids the black screen between streams
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          aspectRatio: aspectRatioValue, 
          facingMode: "user",
        },
        audio: true,
      });

      // Apply zoom by adjusting width/height constraints
      const videoTrack = mediaStream.getVideoTracks()[0];
      if (videoTrack) {
        try {
          // The smaller the zoom value, the wider the view (less zoom)
          const scaleFactor = 2.0 - cameraZoom;  // 0.5 → 1.5, 1.0 → 1.0, 2.0 → 0.0
          
          // Apply width/height scaling based on aspect ratio and zoom level
          const idealWidth = aspectRatioValue >= 1 ? 1920 * scaleFactor : 1080 * scaleFactor;
          const idealHeight = aspectRatioValue >= 1 ? 1080 * scaleFactor : 1920 * scaleFactor;
          
          await videoTrack.applyConstraints({
            width: { ideal: idealWidth },
            height: { ideal: idealHeight }
          });
          console.log("Applied size-based zoom:", scaleFactor);
        } catch (settingsError) {
          console.warn("Could not apply camera zoom settings:", settingsError);
        }
      }

      // Set the new stream to the video element
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }

      // Now stop the old stream after the new one is already displayed
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }

      // Finally update the stream state
      setStream(mediaStream);
      
      // Small delay before removing loading indicator to ensure video is visible
      setTimeout(() => {
        setIsAdjustingCamera(false);
      }, 500);
    } catch (error) {
      setIsAdjustingCamera(false);
      toast({
        title: "Camera access denied",
        description: "Please allow camera access to record video",
        variant: "destructive",
      });
      console.error("Error accessing camera:", error);
    }
  };

  // Initialize camera when component mounts
  useEffect(() => {
    setupCamera(selectedAspectRatio.ratio);
    
    // Cleanup function to stop all tracks when component unmounts
    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [toast]);

  // Update camera when aspect ratio or zoom changes, but with debounce to prevent black screen flashes
  useEffect(() => {
    // Don't update while recording or previewing
    if (isRecording || isPreviewing) return;
    
    // Use a small delay to debounce rapid changes
    const timerId = setTimeout(() => {
      setupCamera(selectedAspectRatio.ratio);
    }, 300);
    
    // Cleanup timeout on next effect run
    return () => clearTimeout(timerId);
  }, [selectedAspectRatio, cameraZoom, isRecording, isPreviewing]);

  useEffect(() => {
    let timer: NodeJS.Timeout;

    if (countdown > 0) {
      timer = setTimeout(() => setCountdown(countdown - 1), 1000);
    } else if (countdown === 0 && isRecording) {
      startRecording();
    }

    return () => clearTimeout(timer);
  }, [countdown, isRecording]);

  useEffect(() => {
    let timer: NodeJS.Timeout;

    if (isRecording && countdown === 0 && !isPaused) {
      timer = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    }

    return () => clearInterval(timer);
  }, [isRecording, countdown, isPaused]);

  const prepareRecording = () => {
    setCountdown(3);
    setIsRecording(true);
  };

  const startRecording = () => {
    if (!stream) return;
    
    // Set up recorder with higher quality options
    const options = { 
      mimeType: 'video/webm;codecs=vp9', // Higher quality codec
      videoBitsPerSecond: 3000000 // 3 Mbps for better quality
    };
    
    // Fall back to standard options if vp9 isn't supported
    const mediaRecorder = options.mimeType && MediaRecorder.isTypeSupported(options.mimeType) 
      ? new MediaRecorder(stream, options)
      : new MediaRecorder(stream);
      
    const chunks: BlobPart[] = [];

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        chunks.push(e.data);
      }
    };

    mediaRecorder.onstop = () => {
      const blob = new Blob(chunks, { type: "video/webm" });
      setRecordedBlob(blob);
      setIsPreviewing(true);

      if (videoRef.current) {
        videoRef.current.srcObject = null;
        videoRef.current.src = URL.createObjectURL(blob);
      }
    };

    setRecordingTime(0);
    mediaRecorder.start();
    mediaRecorderRef.current = mediaRecorder;
  };

  const pauseRecording = () => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === "recording"
    ) {
      mediaRecorderRef.current.pause();
      setIsPaused(true);
    }
  };

  const resumeRecording = () => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === "paused"
    ) {
      mediaRecorderRef.current.resume();
      setIsPaused(false);
    }
  };

  const stopRecording = () => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state !== "inactive"
    ) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setIsPaused(false);
    }
  };

  const resetRecording = () => {
    setIsPreviewing(false);
    setRecordedBlob(null);

    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  };

  const handleUpload = async () => {
    if (!recordedBlob) return;
    
    setIsUploading(true);

    try {
      const timestamp = new Date().getTime();
      const filename = `recording_${timestamp}.webm`;

      // Upload the recording to the server
      const response = await uploadRecordedVideo(recordedBlob, filename);

      if (response && response.filename) {
        // Navigate to processing page with the real filename
        navigate("/processing", {
          state: {
            videoName: "Webcam Recording",
            filename: response.filename,
            aspectRatio: selectedAspectRatio.name,
          },
        });
      } else {
        throw new Error("Upload failed");
      }
    } catch (error) {
      console.error("Upload error:", error);
      toast({
        title: "Upload failed",
        description:
          "There was an error uploading your video. Please try again.",
        variant: "destructive",
      });
      setIsUploading(false);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  // Function to handle zoom adjustment
  const adjustZoom = (newZoom: number) => {
    const adjustedZoom = Math.max(0.5, Math.min(2.0, newZoom)); // Limit zoom between 0.5 and 2.0
    setCameraZoom(adjustedZoom);
    
    // If we already have a camera stream, immediately apply the new zoom
    if (stream) {
      const videoTrack = stream.getVideoTracks()[0];
      if (videoTrack) {
        try {
          const scaleFactor = 2.0 - adjustedZoom;
          const aspectRatioValue = selectedAspectRatio.value;
          
          // Apply width/height scaling based on aspect ratio and zoom level
          const idealWidth = aspectRatioValue >= 1 ? 1920 * scaleFactor : 1080 * scaleFactor;
          const idealHeight = aspectRatioValue >= 1 ? 1080 * scaleFactor : 1920 * scaleFactor;
          
          videoTrack.applyConstraints({
            width: { ideal: idealWidth },
            height: { ideal: idealHeight }
          });
          console.log("Applied size-based zoom:", scaleFactor);
        } catch (settingsError) {
          console.warn("Could not apply camera zoom settings:", settingsError);
        }
      }
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      {/* Video container with dynamic aspect ratio based on selection */}
      <Card className="mb-6 border-2 border-dashed border-border rounded-lg overflow-hidden p-0 w-full sm:max-w-xs mx-auto transition-all duration-300">
        <div className={`relative bg-black ${selectedAspectRatio.cssClass} transition-all duration-300`}>
          <video
            ref={videoRef}
            className={`w-full h-full object-cover ${!isPreviewing ? 'transform scale-x-[-1]' : ''}`}
            autoPlay={!isPreviewing}
            muted={!isPreviewing}
            playsInline
            controls={isPreviewing} // Show video controls in preview mode only
          />

          {countdown > 0 && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/50 text-white">
              <span className="text-7xl font-bold">{countdown}</span>
            </div>
          )}

          {isRecording && countdown === 0 && (
            <div className="absolute top-4 right-4 flex items-center bg-red-500 text-white px-3 py-1 rounded-full">
              <span className="animate-pulse h-3 w-3 rounded-full bg-white mr-2"></span>
              <span className="text-sm font-medium">
                {formatTime(recordingTime)}
              </span>
            </div>
          )}
          
          {/* Show loading indicator when changing camera settings */}
          {isAdjustingCamera && !isRecording && !isPreviewing && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/70 text-white">
              <div className="flex flex-col items-center">
                <div className="animate-spin h-8 w-8 border-4 border-white border-t-transparent rounded-full mb-2"></div>
                <span className="text-sm font-medium">Adjusting camera...</span>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Aspect ratio selection */}
      {!isRecording && !isPreviewing && (
        <div className="mb-6">
          <h3 className="text-lg font-medium mb-2 text-center">Aspect Ratio</h3>
          <div className="flex justify-center items-center gap-3 flex-wrap">
            {ASPECT_RATIO_PRESETS.map((preset) => (
              <Button
                key={preset.name}
                onClick={() => setSelectedAspectRatio(preset)}
                variant="outline"
                className={`px-3 py-1 h-auto transition-all duration-200 ${
                  selectedAspectRatio.name === preset.name 
                    ? "bg-purple-600 text-white hover:bg-purple-700 border-purple-600"
                    : ""
                }`}
              >
                <div className="flex flex-col items-center">
                  <span>{preset.name}</span>
                  <span className="text-xs opacity-70">{preset.description}</span>
                </div>
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* Zoom control - only show when not recording or previewing */}
      {!isRecording && !isPreviewing && (
        <div className="mb-6">
          <h3 className="text-sm font-medium mb-2 text-center">Camera Zoom: {cameraZoom.toFixed(1)}x</h3>
          <div className="flex items-center justify-center gap-3">
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => adjustZoom(cameraZoom - 0.1)}
              disabled={cameraZoom <= 0.5}
              className="px-2 py-1 h-8"
            >
              -
            </Button>
            <div className="w-40 bg-gray-200 h-2 rounded-full">
              <div 
                className="bg-purple-600 h-2 rounded-full" 
                style={{ width: `${((cameraZoom - 0.5) / 1.5) * 100}%` }} 
              />
            </div>
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => adjustZoom(cameraZoom + 0.1)}
              disabled={cameraZoom >= 2.0}
              className="px-2 py-1 h-8"
            >
              +
            </Button>
          </div>
        </div>
      )}

      {/* Modern circular recording controls */}
      <div className="flex flex-wrap justify-center gap-4 mb-4">
        {!isRecording && !isPreviewing && (
          <Button
            onClick={prepareRecording}
            className="h-14 w-14 rounded-full flex items-center justify-center bg-purple-600 hover:bg-purple-700 p-0"
          >
            <Video className="h-7 w-7" />
          </Button>
        )}

        {isRecording && countdown === 0 && !isPaused && (
          <div className="flex gap-4">
            <Button
              onClick={pauseRecording}
              variant="outline"
              className="h-14 w-14 rounded-full flex items-center justify-center border-2 p-0"
            >
              <Pause className="h-6 w-6" />
            </Button>

            <Button
              onClick={stopRecording}
              variant="destructive"
              className="h-14 w-14 rounded-full flex items-center justify-center p-0"
            >
              <Square className="h-6 w-6" />
            </Button>
          </div>
        )}

        {isRecording && countdown === 0 && isPaused && (
          <div className="flex gap-4">
            <Button
              onClick={resumeRecording}
              variant="outline"
              className="h-14 w-14 rounded-full flex items-center justify-center bg-purple-600 hover:bg-purple-700 border-2 p-0 text-white"
            >
              <Video className="h-6 w-6" />
            </Button>

            <Button
              onClick={stopRecording}
              variant="destructive"
              className="h-14 w-14 rounded-full flex items-center justify-center p-0"
            >
              <Square className="h-6 w-6" />
            </Button>
          </div>
        )}
      </div>

      {/* Action buttons for preview mode */}
      {isPreviewing && (
        <div className="flex flex-wrap justify-center gap-4">
          <Button onClick={resetRecording} variant="outline" className="px-8">
            Record Again
          </Button>

          <Button
            onClick={handleUpload}
            disabled={isUploading}
            className="px-8 bg-purple-600 hover:bg-purple-700"
          >
            {isUploading ? "Uploading..." : "Continue with this recording"}
          </Button>
        </div>
      )}
    </div>
  );
};

export default RecordPage;
