
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Upload, Film } from 'lucide-react';
import AppContainer from '@/components/layout/AppContainer';
import { useToast } from '@/hooks/use-toast';
import { uploadVideo } from '@/lib/api';

const UploadPage = () => {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const navigate = useNavigate();
  const { toast } = useToast();

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
      // Upload the file to the API
      const response = await uploadVideo(selectedFile);
      
      if (response && response.filename) {
        toast({
          title: "Upload successful!",
          description: "Your video has been uploaded. Processing will begin now.",
        });
        navigate("/processing", { 
          state: { 
            videoName: selectedFile.name,
            filename: response.filename 
          } 
        });
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
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Upload Video</h1>
        <p className="text-muted-foreground mb-8">
          Upload your video file to begin the AI caption and b-roll generation process.
          We support MP4, MOV, and AVI formats up to 500MB.
        </p>

        <Card 
          className={`border-2 border-dashed ${isDragging ? 'border-purple-500 bg-purple-50' : 'border-border'} rounded-lg p-8 mb-6`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className="flex flex-col items-center justify-center py-10">
            {selectedFile ? (
              <div className="text-center">
                <div className="bg-purple-100 text-purple-700 h-16 w-16 rounded-full flex items-center justify-center mb-4 mx-auto">
                  <Film className="h-8 w-8" />
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
                <div className="bg-muted text-muted-foreground h-16 w-16 rounded-full flex items-center justify-center mb-4 mx-auto">
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

        <div className="flex justify-end">
          <Button
            onClick={handleUpload}
            disabled={!selectedFile || isUploading}
            className="px-8 bg-purple-600 hover:bg-purple-700"
          >
            {isUploading ? "Uploading..." : "Upload & Continue"}
          </Button>
        </div>
      </div>
    </AppContainer>
  );
};

export default UploadPage;
