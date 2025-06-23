// API client for interacting with the backend

/**
 * Get video information by share_id
 * @param shareId The share_id of the video
 * @returns Video info including filename and final video URL if available
 */
export async function getVideoByShareId(shareId: string) {
  try {
    console.log("Fetching video info by share_id:", shareId);
    const response = await fetch(`/api/video/${encodeURIComponent(shareId)}`);
    
    console.log("Video info API response status:", response.status);
    
    if (!response.ok) {
      const errorData = await response.json();
      console.error("Video info API error:", errorData);
      throw new Error(errorData.detail || 'Failed to retrieve video information');
    }
    
    const data = await response.json();
    console.log("Video info API success response:", data);
    return data;
  } catch (error) {
    console.error('Video info fetch error:', error);
    throw error;
  }
}

/**
 * Get final video URL by share_id
 * @param shareId The share_id of the video
 * @returns The URL to the processed final video and other video info
 */
export async function getFinalVideoByShareId(shareId: string) {
  try {
    console.log("Fetching final video URL by share_id:", shareId);
    const response = await fetch(`/api/final_video_by_share/${encodeURIComponent(shareId)}`);
    
    console.log("Final video URL API response status:", response.status);
    
    if (!response.ok) {
      const errorData = await response.json();
      console.error("Final video URL API error:", errorData);
      throw new Error(errorData.detail || 'Failed to get final video URL');
    }
    
    const data = await response.json();
    console.log("Final video URL API success response:", data);
    return data;
  } catch (error) {
    console.error('Final video URL fetch error:', error);
    throw error;
  }
}

/**
 * Upload a video file to the server
 * @param file The video file to upload
 * @returns Response with filename, status and URL
 */
export async function uploadVideo(file: File) {
  // Add timestamp to filename to avoid duplicates
  const timestamp = Date.now();
  const fileExtension = file.name.split('.').pop();
  const fileNameWithoutExt = file.name.replace(/\.[^/.]+$/, ""); // Remove extension
  const newFileName = `${fileNameWithoutExt}_${timestamp}.${fileExtension}`;
  
  // Create a new File object with the timestamped name
  const timestampedFile = new File([file], newFileName, { type: file.type });
  
  const formData = new FormData();
  formData.append('file', timestampedFile);

  try {
    console.log(`Uploading file with timestamped name: ${newFileName}`);
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Failed to upload video');
    }

    return await response.json();
  } catch (error) {
    console.error('Upload error:', error);
    throw error;
  }
}

/**
 * Upload a Blob from a recorded video
 * @param blob The blob containing video data 
 * @param filename Optional filename (defaults to timestamp)
 * @returns Response with filename, status and URL
 */
export async function uploadRecordedVideo(blob: Blob, filename?: string) {
  const file = new File(
    [blob], 
    filename || `recording_${Date.now()}.webm`, 
    { type: blob.type }
  );
  
  return uploadVideo(file);
}

/**
 * Generate captions for a video
 * @param filename The filename of the uploaded video
 * @returns Status of the caption generation task
 */
export async function generateCaptions(filename: string) {
  try {
    console.log("Starting caption generation API call for filename:", filename);
    // Send filename as a query parameter instead of in the body
    const response = await fetch(`/api/generate_captions?filename=${encodeURIComponent(filename)}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    console.log("Caption generation API response status:", response.status);
    
    if (!response.ok) {
      const errorData = await response.json();
      console.error("Caption generation API error:", errorData);
      throw new Error(errorData.detail || 'Failed to generate captions');
    }

    const data = await response.json();
    console.log("Caption generation API success response:", data);
    return data;
  } catch (error) {
    console.error('Caption generation error:', error);
    throw error;
  }
}

/**
 * Get the transcript for a video
 * @param filename The filename of the video
 * @returns The transcript data
 */
export async function getTranscript(filename: string) {
  try {
    console.log("Fetching transcript for filename:", filename);
    // Get transcript data from the backend
    const response = await fetch(`/api/transcript/${encodeURIComponent(filename)}`);
    
    console.log("Transcript API response status:", response.status);

    if (!response.ok) {
      const errorData = await response.json();
      console.error("Transcript API error:", errorData);
      throw new Error(errorData.detail || 'Failed to retrieve transcript');
    }

    const data = await response.json();
    console.log("Transcript API success response received");
    return data;
  } catch (error) {
    console.error('Transcript fetch error:', error);
    throw error;
  }
}

/**
 * Get B-roll imagery for a text prompt
 * @param prompt The text prompt to generate B-roll for
 * @returns URL to the generated B-roll
 */
export async function getBRoll(prompt: string) {
  try {
    console.log("Requesting B-roll for prompt:", prompt);
    // Match endpoint format in backend - we need to send prompt in body, NOT as query param
    const response = await fetch(`/api/broll`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ prompt })
    });

    console.log("B-roll response status:", response.status);
    
    if (!response.ok) {
      const errorData = await response.json();
      console.error("B-roll API error:", errorData);
      throw new Error(errorData.detail || 'Failed to generate B-roll');
    }

    const data = await response.json();
    console.log("B-roll API success response:", data);
    return data;
  } catch (error) {
    console.error('B-roll generation error:', error);
    throw error;
  }
}

/**
 * Generate the final video with captions and B-roll
 * @param filename The filename of the uploaded video
 * @returns Status of the final video generation process
 */
export async function generateFinalVideo(filename: string) {
  try {
    console.log("Starting final video generation for:", filename);
    const response = await fetch(`/api/generate_final_video?filename=${encodeURIComponent(filename)}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    console.log("Final video generation API response status:", response.status);
    
    if (!response.ok) {
      const errorData = await response.json();
      console.error("Final video generation API error:", errorData);
      throw new Error(errorData.detail || 'Failed to generate final video');
    }

    const data = await response.json();
    console.log("Final video generation API success response:", data);
    return data;
  } catch (error) {
    console.error('Final video generation error:', error);
    throw error;
  }
}

/**
 * Get the URL of the processed final video
 * @param filename The filename of the original video
 * @returns The URL to the processed final video
 */
export async function getFinalVideoUrl(filename: string) {
  try {
    console.log("Fetching final video URL for:", filename);
    const response = await fetch(`/api/final_video/${encodeURIComponent(filename)}`);
    
    console.log("Final video URL API response status:", response.status);
    
    if (!response.ok) {
      const errorData = await response.json();
      console.error("Final video URL API error:", errorData);
      throw new Error(errorData.detail || 'Failed to get final video URL');
    }
    
    const data = await response.json();
    console.log("Final video URL API success response:", data);
    return data;
  } catch (error) {
    console.error('Final video URL fetch error:', error);
    throw error;
  }
}