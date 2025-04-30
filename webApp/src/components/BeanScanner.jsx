import React, { useState, useRef, useEffect } from "react";
import Button from "../components/Button.jsx";

const BeanScanner = ({ onScanComplete, slotIndex, onCancel }) => {
  // State
  const [frontImage, setFrontImage] = useState(null);
  const [backImage, setBackImage] = useState(null);
  const [currentSide, setCurrentSide] = useState("front");
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [message, setMessage] = useState("Starting camera automatically...");
  const [processing, setProcessing] = useState(false);
  
  // Refs
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const guideCanvasRef = useRef(null);
  const streamRef = useRef(null);
  
  // Guide rectangle dimensions (cache to avoid recalculating)
  const [guideRect, setGuideRect] = useState(null);
  
  // Default bean information
  const defaultBeanInfo = {
    name: `Unknown Coffee ${slotIndex}`,
    type: "arabica",
    roast: "medium",
    notes: "No flavor notes detected"
  };
  
  // Start camera automatically when component mounts
  useEffect(() => {
    startCamera();
    
    // Clean up when component unmounts
    return () => {
      stopCamera();
    };
  }, []);
  
  // Draw user guide when camera is on
  useEffect(() => {
    if (isCameraOn) {
      drawUserGuide();
    }
  }, [isCameraOn]);
  
  // Simple camera start
  const startCamera = async () => {
    try {
      setMessage("Starting camera...");
      
      if (!videoRef.current) {
        setMessage("Camera element not available");
        return;
      }
      
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        streamRef.current = stream;
        setIsCameraOn(true);
        setMessage(`Position the ${currentSide} of the coffee bag within the guide and click 'Capture'`);
      }
    } catch (err) {
      console.error("Camera error:", err);
      setMessage(`Camera error: ${err.message}`);
    }
  };
  
  // Simple camera stop
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    
    setIsCameraOn(false);
  };
  
  // Draw user guide on the guide canvas
  const drawUserGuide = () => {
    if (!guideCanvasRef.current || !videoRef.current) return;
    
    const canvas = guideCanvasRef.current;
    const ctx = canvas.getContext('2d');
    
    // Wait for video to get its dimensions
    const checkVideoDimensions = setInterval(() => {
      if (videoRef.current && videoRef.current.videoWidth) {
        clearInterval(checkVideoDimensions);
        
        // Set canvas size to match video
        canvas.width = videoRef.current.videoWidth || 640;
        canvas.height = videoRef.current.videoHeight || 480;
        
        // Clear previous drawings
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Calculate guide rectangle (about 70% of the frame)
        const guideWidth = canvas.width * 0.7;
        const guideHeight = canvas.height * 0.7;
        const guideX = (canvas.width - guideWidth) / 2;
        const guideY = (canvas.height - guideHeight) / 2;
        
        // Store the guide rectangle for later use
        setGuideRect({
          x: guideX,
          y: guideY,
          width: guideWidth,
          height: guideHeight
        });
        
        // Draw semi-transparent overlay
        ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
        
        // Top section
        ctx.fillRect(0, 0, canvas.width, guideY);
        // Bottom section
        ctx.fillRect(0, guideY + guideHeight, canvas.width, canvas.height - (guideY + guideHeight));
        // Left section
        ctx.fillRect(0, guideY, guideX, guideHeight);
        // Right section
        ctx.fillRect(guideX + guideWidth, guideY, canvas.width - (guideX + guideWidth), guideHeight);
        
        // Draw guide rectangle
        ctx.strokeStyle = '#FFFFFF';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]); // Dashed line
        ctx.strokeRect(guideX, guideY, guideWidth, guideHeight);
        
        // Draw corner guides
        const cornerSize = 20;
        ctx.setLineDash([]); // Solid line for corners
        ctx.beginPath();
        
        // Top-left corner
        ctx.moveTo(guideX, guideY + cornerSize);
        ctx.lineTo(guideX, guideY);
        ctx.lineTo(guideX + cornerSize, guideY);
        
        // Top-right corner
        ctx.moveTo(guideX + guideWidth - cornerSize, guideY);
        ctx.lineTo(guideX + guideWidth, guideY);
        ctx.lineTo(guideX + guideWidth, guideY + cornerSize);
        
        // Bottom-right corner
        ctx.moveTo(guideX + guideWidth, guideY + guideHeight - cornerSize);
        ctx.lineTo(guideX + guideWidth, guideY + guideHeight);
        ctx.lineTo(guideX + guideWidth - cornerSize, guideY + guideHeight);
        
        // Bottom-left corner
        ctx.moveTo(guideX + cornerSize, guideY + guideHeight);
        ctx.lineTo(guideX, guideY + guideHeight);
        ctx.lineTo(guideX, guideY + guideHeight - cornerSize);
        
        ctx.strokeStyle = '#FFFFFF';
        ctx.lineWidth = 3;
        ctx.stroke();
        
        // Add label
        ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        ctx.fillRect(guideX, guideY - 25, 230, 20);
        ctx.fillStyle = '#FFFFFF';
        ctx.font = '12px Arial';
        ctx.fillText('Position coffee bag within this area', guideX + 5, guideY - 10);
      }
    }, 100);
  };
  
  // Simple capture using the guide rectangle
  const captureImage = () => {
    if (!videoRef.current || !canvasRef.current || !guideRect) {
      setMessage("Cannot capture - video not ready or guide not available");
      return;
    }
    
    try {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      
      // Set canvas size
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      
      // Draw video frame to canvas
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      
      // Create a new canvas for the cropped image
      const croppedCanvas = document.createElement('canvas');
      const croppedCtx = croppedCanvas.getContext('2d');
      
      // Set cropped canvas size to guide dimensions
      croppedCanvas.width = guideRect.width;
      croppedCanvas.height = guideRect.height;
      
      // Draw only the guide region to the cropped canvas
      croppedCtx.drawImage(
        canvas,
        guideRect.x, guideRect.y, guideRect.width, guideRect.height, // Source area
        0, 0, guideRect.width, guideRect.height // Destination area
      );
      
      // Get the cropped image data
      const imageData = croppedCanvas.toDataURL('image/jpeg', 0.95);
      
      // Save image based on current side
      if (currentSide === "front") {
        setFrontImage(imageData);
        setCurrentSide("back");
        setMessage("Front captured! Now position and capture the BACK of the bag.");
      } else {
        setBackImage(imageData);
        setMessage("Back captured! Processing...");
        processImages(frontImage, imageData);
      }
    } catch (error) {
      console.error("Capture error:", error);
      setMessage(`Error capturing: ${error.message}`);
    }
  };
  
  // Process images with API
  const processImages = async (frontImage, backImage) => {
    setProcessing(true);
    
    try {
      // Extract base64 data
      const frontImageBase64 = frontImage.split(',')[1];
      const backImageBase64 = backImage.split(',')[1];
      
      // Prepare API request
      const apiRequestData = {
        front_image: frontImageBase64,
        back_image: backImageBase64,
        slot_index: slotIndex
      };
      
      // Send to API
      const response = await fetch("http://localhost:8000/api/process-coffee-bag", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(apiRequestData)
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      // Process response
      const data = await response.json();
      
      // Check if detection successful
      if (data.detection_status === "failed" || !data.name) {
        setMessage("Detection failed. Using default values.");
        onScanComplete(slotIndex, defaultBeanInfo);
      } else {
        // Process successful data
        const beanInfo = {
          name: data.name || defaultBeanInfo.name,
          type: data.type || defaultBeanInfo.type,
          roast: data.roast ? data.roast.toLowerCase() : defaultBeanInfo.roast,
          notes: data.notes || defaultBeanInfo.notes
        };
        
        setMessage(`Successfully identified: ${beanInfo.name}`);
        onScanComplete(slotIndex, beanInfo);
      }
    } catch (error) {
      console.error("Error:", error);
      setMessage(`Error: ${error.message}. Using default values.`);
      onScanComplete(slotIndex, defaultBeanInfo);
    } finally {
      setProcessing(false);
      stopCamera();
    }
  };
  
  // Handle cancel
  const handleCancel = () => {
    stopCamera();
    onCancel();
  };
  
  // Handle restart camera
  const handleRestartCamera = () => {
    stopCamera();
    startCamera();
  };
  
  return (
    <div className="bg-white rounded p-4 mb-6">
      <h3 className="text-lg font-semibold mb-3">Scan Coffee Bag for Slot {slotIndex}</h3>
      
      {/* Status message */}
      <div className="mb-4 p-2 bg-gray-100 rounded text-sm">
        {message}
      </div>
      
      {/* Video preview with overlay */}
      <div className="mb-4 bg-black rounded relative" style={{ height: "300px" }}>
        {/* Video element */}
        <video
          ref={videoRef}
          style={{ width: "100%", height: "100%", objectFit: "contain" }}
          autoPlay
          playsInline
          muted
        />
        
        {/* Guide canvas overlay */}
        <canvas
          ref={guideCanvasRef}
          className="absolute inset-0 w-full h-full"
          style={{ pointerEvents: "none" }}
        />
        
        {/* Hidden canvas for capturing */}
        <canvas ref={canvasRef} style={{ display: "none" }} />
      </div>
      
      {/* Preview images */}
      <div className="flex gap-2 mb-4">
        <div className="w-1/2">
          <p className="text-xs font-medium mb-1">Front</p>
          {frontImage ? (
            <img 
              src={frontImage} 
              alt="Front of coffee bag" 
              className="w-full h-32 object-contain border rounded bg-gray-100"
            />
          ) : (
            <div className="w-full h-32 bg-gray-200 border rounded flex items-center justify-center text-sm text-gray-500">
              Not captured
            </div>
          )}
        </div>
        <div className="w-1/2">
          <p className="text-xs font-medium mb-1">Back</p>
          {backImage ? (
            <img 
              src={backImage} 
              alt="Back of coffee bag" 
              className="w-full h-32 object-contain border rounded bg-gray-100"
            />
          ) : (
            <div className="w-full h-32 bg-gray-200 border rounded flex items-center justify-center text-sm text-gray-500">
              Not captured
            </div>
          )}
        </div>
      </div>
      
      {/* Button controls */}
      <div className="flex gap-2 justify-center">
        {!isCameraOn && !processing && (
          <Button 
            text="Restart Camera" 
            onClick={handleRestartCamera} 
            color="#386150"
          />
        )}
        
        {isCameraOn && !processing && (
          <Button 
            text={`Capture ${currentSide}`} 
            onClick={captureImage} 
            color="#386150"
          />
        )}
        
        <Button 
          text={processing ? "Processing..." : "Cancel"} 
          onClick={handleCancel} 
          color="#DD6B55"
          disabled={processing}
        />
      </div>
      
      {/* Instructions */}
      {!processing && isCameraOn && (
        <div className="mt-4 text-xs text-center text-gray-600">
          Position the coffee bag within the dashed rectangle for best results
        </div>
      )}
    </div>
  );
};

export default BeanScanner;