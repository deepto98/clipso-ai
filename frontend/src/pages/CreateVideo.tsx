
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Camera, Upload, Video } from 'lucide-react';
import AppContainer from '@/components/layout/AppContainer';
import { useToast } from '@/hooks/use-toast';
import { uploadVideo } from '@/lib/api';
import RecordPage from './Record';
import PageHeading from '@/components/ui/page-heading';

const CreateVideo = () => {
  const [activeTab, setActiveTab] = useState<string>("upload");
  
  // Upload state
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  
  const navigate = useNavigate();
  const { toast } = useToast();

  // Handle Upload functionality
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type.startsWith('video/')) {
      setSelectedFile(files[0]);
    } else {
      toast({
        title: "Invalid file type",
        description: "Please upload a video file",
        variant: "destructive",
      });
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0 && files[0].type.startsWith('video/')) {
      setSelectedFile(files[0]);
    } else {
      toast({
        title: "Invalid file type",
        description: "Please upload a video file",
        variant: "destructive",
      });
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    
    try {
      const response = await uploadVideo(selectedFile);
      
      if (response.success) {
        toast({
          title: "Upload successful!",
          description: "Your video has been uploaded. Processing will begin now.",
        });
        // Navigate to processing page with the filename
        navigate("/processing", { state: { videoName: selectedFile.name, filename: response.filename } });
      } else {
        throw new Error("Upload failed");
      }
    } catch (error) {
      console.error("Upload error:", error);
      toast({
        title: "Upload failed",
        description: "There was an error uploading your video. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <AppContainer>
      <div className="max-w-4xl mx-auto">
        <PageHeading 
          title="Create New Video"
          description="Upload a video file or record directly from your webcam to begin the AI captions and b-roll generation process."
        />

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid grid-cols-2 w-full mb-8 bg-secondary/50 backdrop-blur-sm rounded-xl p-1">
            <TabsTrigger 
              value="upload" 
              className="flex items-center gap-2 data-[state=active]:bg-purple-600 data-[state=active]:hover:bg-purple-700 data-[state=active]:text-white transition-all duration-200"
            >
              <Upload className="h-4 w-4" />
              Upload Video
            </TabsTrigger>
            <TabsTrigger 
              value="record" 
              className="flex items-center gap-2 data-[state=active]:bg-purple-600 data-[state=active]:hover:bg-purple-700 data-[state=active]:text-white transition-all duration-200"
            >
              <Camera className="h-4 w-4" />
              Record Video
            </TabsTrigger>
          </TabsList>

          {/* Upload Tab Content */}
          <TabsContent value="upload" className="mt-0">
            <Card 
              className={`border-2 border-dashed backdrop-blur-md ${isDragging ? 'border-purple-500 bg-purple-900/10' : 'border-border'} rounded-xl p-8 mb-6 glass-card`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <div className="flex flex-col items-center justify-center py-10">
                {selectedFile ? (
                  <div className="text-center">
                    <div className="bg-purple-900/30 text-purple-300 h-16 w-16 rounded-full flex items-center justify-center mb-4 mx-auto">
                      <Video className="h-8 w-8" />
                    </div>
                    <p className="text-lg font-medium mb-2">{selectedFile.name}</p>
                    <p className="text-sm text-muted-foreground mb-4">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                    <Button 
                      onClick={() => setSelectedFile(null)} 
                      variant="outline" 
                      className="text-sm"
                    >
                      Change File
                    </Button>
                  </div>
                ) : (
                  <div className="text-center">
                    <div className="bg-purple-900/30 text-purple-300 h-16 w-16 rounded-full flex items-center justify-center mb-4 mx-auto">
                      <Upload className="h-8 w-8" />
                    </div>
                    <p className="text-lg font-medium mb-2">Drag & drop your video here</p>
                    <p className="text-sm text-muted-foreground mb-4">or click to browse files</p>
                    <label htmlFor="file-upload">
                      <input
                        id="file-upload"
                        type="file"
                        accept="video/*"
                        className="sr-only"
                        onChange={handleFileChange}
                      />
                      <Button variant="outline" className="cursor-pointer" asChild>
                        <span>Browse Files</span>
                      </Button>
                    </label>
                  </div>
                )}
              </div>
            </Card>

            <div className="flex justify-center">
              <Button
                onClick={handleUpload}
                disabled={!selectedFile || isUploading}
                className="px-8 bg-purple-600 hover:bg-purple-700 button-glow"
              >
                {isUploading ? "Uploading..." : "Upload & Continue"}
              </Button>
            </div>
          </TabsContent>

          {/* Record Tab Content */}
          <TabsContent value="record" className="mt-0">
            {/* Use the RecordPage component directly */}
            <div className="recordPageWrapper">
              <RecordPage />
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </AppContainer>
  );
};

export default CreateVideo;
