import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import AppContainer from '@/components/layout/AppContainer';
import { Card } from '@/components/ui/card';
import { generateCaptions, getTranscript, getBRoll, generateFinalVideo, getFinalVideoUrl } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import PageHeading from '@/components/ui/page-heading';

interface ProcessingStep {
  id: string;
  name: string;
  status: 'waiting' | 'processing' | 'completed' | 'error';
  progress: number;
}

const ProcessingPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { videoName, filename } = location.state || { videoName: "Your video", filename: null };
  
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [overallProgress, setOverallProgress] = useState(0);
  // Add processing flags to prevent duplicate API calls
  const [isProcessingStarted, setIsProcessingStarted] = useState(false);
  const [isBrollProcessing, setIsBrollProcessing] = useState(false);
  const [steps, setSteps] = useState<ProcessingStep[]>([
    { id: 'upload', name: 'Video Upload', status: 'completed', progress: 100 },
    { id: 'transcription', name: 'Generating Transcription', status: 'processing', progress: 0 },
    { id: 'captions', name: 'Creating Captions', status: 'waiting', progress: 0 },
    { id: 'broll', name: 'Finding B-Roll Footage', status: 'waiting', progress: 0 },
    { id: 'rendering', name: 'Rendering Final Video', status: 'waiting', progress: 0 },
  ]);

  // Helper function to create shareable URL ID from filename
  const getShareableId = (filename: string) => {
    return encodeURIComponent(filename.replace(/\.[^/.]+$/, "")); // Remove file extension
  };

  // Debug log the state to help diagnose issues
  useEffect(() => {
    console.log("Processing page loaded with state:", { videoName, filename });
  }, []);
  
  // Process steps with real API calls
  useEffect(() => {
    // If we don't have a filename, we can't continue
    if (!filename) {
      console.error("No filename provided in state");
      toast({
        title: "Processing error",
        description: "No video filename provided. Please upload a video first.",
        variant: "destructive"
      });
      navigate('/create');
      return;
    }
    
    // Immediately start caption generation on load
    const initiateProcessing = async () => {
      // Only initiate processing once
      if (isProcessingStarted) {
        console.log("Processing already started, skipping duplicate initialization");
        return;
      }
      
      setIsProcessingStarted(true);
      
      try {
        console.log("Initiating caption generation for:", filename);
        await generateCaptions(filename);
        console.log("Caption generation request successful");
        
        // Schedule status checks every few seconds
        let attempts = 0;
        const maxAttempts = 20; // Max number of attempts before giving up
        
        // Use a function to check transcript status with incrementing attempts
        const checkTranscriptStatus = async () => {
          if (attempts >= maxAttempts) {
            console.error(`Exceeded maximum attempts (${maxAttempts}) checking for transcript`);
            // Show error message but continue with default processing
            toast({
              title: "Transcript Processing Warning",
              description: "Taking longer than expected to process the transcript. Continuing with limited functionality.",
              variant: "destructive"
            });
            
            // Skip ahead to rendering with defaults
            setSteps(prevSteps => {
              const newSteps = [...prevSteps];
              newSteps[1].status = 'completed';
              newSteps[1].progress = 100;
              newSteps[2].status = 'completed';
              newSteps[2].progress = 100;
              newSteps[3].status = 'completed'; // Skip B-roll
              newSteps[3].progress = 100;
              newSteps[4].status = 'processing'; // Go to rendering
              newSteps[4].progress = 0;
              return newSteps;
            });
            
            setCurrentStepIndex(4);
            return;
          }
          
          attempts++; // Increment counter before API call
          console.log(`Status check attempt ${attempts} for ${filename}`);
          
          try {
            console.log("Fetching transcript for filename:", filename);
            const transcript = await getTranscript(filename);
            console.log("Transcript now available:", transcript);
            
            // Update step status - assume transcription and captions are complete
            setSteps(prevSteps => {
              const newSteps = [...prevSteps];
              // Transcription complete
              newSteps[1].status = 'completed';
              newSteps[1].progress = 100;
              
              // Captions complete
              newSteps[2].status = 'completed';
              newSteps[2].progress = 100;
              
              // B-roll processing
              newSteps[3].status = 'processing';
              newSteps[3].progress = 0;
              
              return newSteps;
            });
            
            // Move to b-roll processing
            setCurrentStepIndex(3);
            
            // Start b-roll processing immediately (only if not already processing)
            if (isBrollProcessing) {
              console.log("B-roll processing already started, skipping duplicate call");
              return;
            }
            
            setIsBrollProcessing(true);
            
            const transcriptText = typeof transcript === 'string' 
              ? transcript 
              : transcript.text || JSON.stringify(transcript).slice(0, 100);
            
            console.log("Starting B-roll generation with prompt from transcript:", transcriptText);
            const brollPrompt = `High quality visual scene representing: ${transcriptText.split('.')[0]}`;
            console.log("Final B-roll prompt:", brollPrompt);
            
            try {
              const brollResponse = await getBRoll(brollPrompt);
              console.log("B-roll generation successful:", brollResponse);
              
              // Update broll step to complete
              setSteps(prevSteps => {
                const newSteps = [...prevSteps];
                newSteps[3].status = 'completed';
                newSteps[3].progress = 100;
                
                // Rendering step
                newSteps[4].status = 'processing';
                newSteps[4].progress = 10; // Start at 10% to show immediate progress
                
                return newSteps;
              });
              
              // Move to rendering step
              setCurrentStepIndex(4);
              
              // Start real final video generation process
              console.log("Starting final video generation for:", filename);
              try {
                // Trigger final video generation API
                const finalVideoResponse = await generateFinalVideo(filename);
                console.log("Final video generation initiated:", finalVideoResponse);
                
                // Set up polling to check final video status
                let finalVideoAttempts = 0;
                const maxFinalVideoAttempts = 30; // Allow more attempts for final video rendering
                const checkFinalVideoStatus = async () => {
                  if (finalVideoAttempts >= maxFinalVideoAttempts) {
                    console.error(`Exceeded maximum attempts (${maxFinalVideoAttempts}) checking for final video`);
                    
                    toast({
                      title: "Rendering Warning",
                      description: "Taking longer than expected to render the video. You can still preview the result.",
                      variant: "destructive"
                    });
                    
                    // Mark as complete anyway and navigate to preview
                    setSteps(prevSteps => {
                      const newSteps = [...prevSteps];
                      newSteps[4].status = 'completed';
                      newSteps[4].progress = 100;
                      return newSteps;
                    });
                    
                    // Navigate to preview with shareable URL
                    const videoId = getShareableId(filename);
                    navigate(`/preview/${videoId}`, { state: { filename } });
                    return;
                  }
                  
                  finalVideoAttempts++;
                  console.log(`Final video check attempt ${finalVideoAttempts} for ${filename}`);
                  
                  try {
                    // Try to get the final video URL
                    const finalVideoData = await getFinalVideoUrl(filename);
                    console.log("Final video is ready:", finalVideoData);
                    
                    // Final video is ready, update progress to complete
                    setSteps(prevSteps => {
                      const newSteps = [...prevSteps];
                      newSteps[4].status = 'completed';
                      newSteps[4].progress = 100;
                      return newSteps;
                    });
                    
                    // Navigate to shareable preview URL with the final video data
                    // Use share_id from API response if available
                    const shareId = finalVideoData.share_id;
                    if (!shareId) {
                      console.error("No share_id returned from API, using fallback");
                    }
                    const videoId = shareId || getShareableId(filename);
                    
                    console.log("Using share_id for navigation:", videoId);
                    
                    setTimeout(() => {
                      navigate(`/preview/${videoId}`, { 
                        state: { 
                          filename,
                          finalVideoUrl: finalVideoData.final_video_url,
                          shareId: videoId // Pass share_id explicitly
                        } 
                      });
                    }, 1000);
                    
                  } catch (e) {
                    console.log("Final video not ready yet, will retry...", e);
                    
                    // Update progress based on attempts (max 95%)
                    const progress = Math.min(10 + Math.floor((finalVideoAttempts / maxFinalVideoAttempts) * 85), 95);
                    setSteps(prevSteps => {
                      const newSteps = [...prevSteps];
                      newSteps[4].progress = progress;
                      return newSteps;
                    });
                    
                    // Schedule next check
                    setTimeout(checkFinalVideoStatus, 3000);
                  }
                };
                
                // Start checking for final video status
                checkFinalVideoStatus();
                
              } catch (finalVideoError) {
                console.error("Failed to start final video generation:", finalVideoError);
                
                toast({
                  title: "Rendering Error",
                  description: "Failed to start final video generation. You can still preview the original video.",
                  variant: "destructive"
                });
                
                // Mark rendering as error but still allow preview
                setSteps(prevSteps => {
                  const newSteps = [...prevSteps];
                  newSteps[4].status = 'error';
                  newSteps[4].progress = 100;
                  return newSteps;
                });
                
                // Navigate to preview after delay with shareable URL
                const videoId = getShareableId(filename);
                setTimeout(() => {
                  navigate(`/preview/${videoId}`, { state: { filename } });
                }, 1500);
              }
              
            } catch (brollError) {
              console.error("B-roll generation failed:", brollError);
              
              // Mark B-roll as error but continue to rendering
              setSteps(prevSteps => {
                const newSteps = [...prevSteps];
                newSteps[3].status = 'error';
                newSteps[3].progress = 100;
                
                // Continue to rendering anyway
                newSteps[4].status = 'processing';
                newSteps[4].progress = 10; // Start at 10% to show immediate progress
                
                return newSteps;
              });
              
              // Move to rendering step
              setCurrentStepIndex(4);
              
              // Start real final video generation process even when B-roll fails
              console.log("Starting final video generation without B-roll for:", filename);
              try {
                // Trigger final video generation API 
                const finalVideoResponse = await generateFinalVideo(filename);
                console.log("Final video generation initiated (without B-roll):", finalVideoResponse);
                
                // Set up polling to check final video status
                let finalVideoAttempts = 0;
                const maxFinalVideoAttempts = 30; // Allow more attempts for final video rendering
                const checkFinalVideoStatus = async () => {
                  if (finalVideoAttempts >= maxFinalVideoAttempts) {
                    console.error(`Exceeded maximum attempts (${maxFinalVideoAttempts}) checking for final video`);
                    
                    toast({
                      title: "Rendering Warning",
                      description: "Taking longer than expected to render the video. You can still preview the result.",
                      variant: "destructive"
                    });
                    
                    // Mark as complete anyway and navigate to preview
                    setSteps(prevSteps => {
                      const newSteps = [...prevSteps];
                      newSteps[4].status = 'completed';
                      newSteps[4].progress = 100;
                      return newSteps;
                    });
                    
                    // Navigate to preview with shareable URL
                    const videoId = getShareableId(filename);
                    navigate(`/preview/${videoId}`, { state: { filename } });
                    return;
                  }
                  
                  finalVideoAttempts++;
                  console.log(`Final video check attempt ${finalVideoAttempts} for ${filename}`);
                  
                  try {
                    // Try to get the final video URL
                    const finalVideoData = await getFinalVideoUrl(filename);
                    console.log("Final video is ready (without B-roll):", finalVideoData);
                    
                    // Final video is ready, update progress to complete
                    setSteps(prevSteps => {
                      const newSteps = [...prevSteps];
                      newSteps[4].status = 'completed';
                      newSteps[4].progress = 100;
                      return newSteps;
                    });
                    
                    // Navigate to shareable preview URL with the final video data
                    // Use share_id from API response if available
                    const shareId = finalVideoData.share_id;
                    if (!shareId) {
                      console.error("No share_id returned from API, using fallback");
                    }
                    const videoId = shareId || getShareableId(filename);
                    
                    console.log("Using share_id for navigation:", videoId);
                    
                    setTimeout(() => {
                      navigate(`/preview/${videoId}`, { 
                        state: { 
                          filename,
                          finalVideoUrl: finalVideoData.final_video_url,
                          shareId: videoId // Pass share_id explicitly
                        } 
                      });
                    }, 1000);
                    
                  } catch (e) {
                    console.log("Final video not ready yet, will retry...", e);
                    
                    // Update progress based on attempts (max 95%)
                    const progress = Math.min(10 + Math.floor((finalVideoAttempts / maxFinalVideoAttempts) * 85), 95);
                    setSteps(prevSteps => {
                      const newSteps = [...prevSteps];
                      newSteps[4].progress = progress;
                      return newSteps;
                    });
                    
                    // Schedule next check
                    setTimeout(checkFinalVideoStatus, 3000);
                  }
                };
                
                // Start checking for final video status
                checkFinalVideoStatus();
                
              } catch (finalVideoError) {
                console.error("Failed to start final video generation (without B-roll):", finalVideoError);
                
                toast({
                  title: "Rendering Error",
                  description: "Failed to generate final video. You can still preview the original.",
                  variant: "destructive"
                });
                
                // Mark rendering as error but still allow preview
                setSteps(prevSteps => {
                  const newSteps = [...prevSteps];
                  newSteps[4].status = 'error';
                  newSteps[4].progress = 100;
                  return newSteps;
                });
                
                // Navigate to preview after delay with shareable URL
                const videoId = getShareableId(filename);
                setTimeout(() => {
                  navigate(`/preview/${videoId}`, { state: { filename } });
                }, 1500);
              }
            }
            
          } catch (e) {
            console.log("Transcript not ready yet, will retry...", e);
            
            // Update transcription progress based on attempts
            const progress = Math.min(10 + (attempts * 5), 95);
            setSteps(prevSteps => {
              const newSteps = [...prevSteps];
              newSteps[1].progress = progress;
              return newSteps;
            });
            
            // Schedule next check after delay
            setTimeout(checkTranscriptStatus, 3000);
          }
        };
        
        // Start the first check
        checkTranscriptStatus();
        
      } catch (error) {
        console.error("Failed to start caption generation:", error);
        toast({
          title: "Processing error",
          description: "Failed to start caption generation. Please try again.",
          variant: "destructive"
        });
      }
    };
    
    initiateProcessing();

    // Our entire process is now handled in the initiateProcessing function
    // No need for separate step processing logic
    
    return () => {
      // Cleanup will be handled by the individual interval clear functions
    };
    
  }, [currentStepIndex, steps, filename, navigate, toast, isProcessingStarted, isBrollProcessing]);

  // Calculate overall progress
  useEffect(() => {
    const totalProgress = steps.reduce((sum, step) => sum + step.progress, 0);
    setOverallProgress(Math.round(totalProgress / steps.length));
  }, [steps]);

  return (
    <AppContainer>
      <div className="max-w-3xl mx-auto">
        <PageHeading 
          title="Processing Video"
          description={`Clipso is working its magic on "${videoName}". This process typically takes 3-5 minutes. You can stay on this page or come back later - we'll save your progress.`}
        />
        
        <Card className="p-6 mb-8">
          <div className="mb-4">
            <div className="flex justify-between items-center mb-2">
              <span className="font-medium">Overall Progress</span>
              <span className="text-sm text-muted-foreground">{overallProgress}%</span>
            </div>
            <Progress value={overallProgress} className="h-2" />
          </div>
          
          <div className="space-y-6">
            {steps.map((step, index) => (
              <div key={step.id} className="space-y-2">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    {step.status === 'waiting' && (
                      <div className="h-5 w-5 rounded-full border-2 border-muted"></div>
                    )}
                    {step.status === 'processing' && (
                      <div className="h-5 w-5 rounded-full border-2 border-t-transparent border-purple-500 animate-spin"></div>
                    )}
                    {step.status === 'completed' && (
                      <div className="h-5 w-5 rounded-full bg-green-500 flex items-center justify-center">
                        <svg className="h-3 w-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                      </div>
                    )}
                    {step.status === 'error' && (
                      <div className="h-5 w-5 rounded-full bg-red-500 flex items-center justify-center">
                        <svg className="h-3 w-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                      </div>
                    )}
                    <span className={step.status === 'error' ? 'text-red-500' : ''}>{step.name}</span>
                  </div>
                  <span className="text-sm text-muted-foreground">{step.progress}%</span>
                </div>
                <Progress value={step.progress} className={`h-1.5 ${step.status === 'error' ? 'bg-red-200' : ''}`} />
              </div>
            ))}
          </div>
        </Card>
        
        <div className="text-center">
          <p className="text-sm text-muted-foreground mb-2">Need to leave? We'll keep processing in the background.</p>
          <Button 
            variant="outline" 
            onClick={() => navigate('/')}
            className="mx-auto"
          >
            Return to Homepage
          </Button>
        </div>
      </div>
    </AppContainer>
  );
};

export default ProcessingPage;