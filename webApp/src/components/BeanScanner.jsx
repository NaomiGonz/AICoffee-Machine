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
  const [boundaryRect, setBoundaryRect] = useState(null);
  const [showBoundary, setShowBoundary] = useState(false);
  const [boundaryStable, setBoundaryStable] = useState(false);
  const [boundaryStableCount, setBoundaryStableCount] = useState(0);
  
  // Refs
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const boundaryCanvasRef = useRef(null);
  const streamRef = useRef(null);
  const boundaryDetectionRef = useRef(null);
  const stableTimeoutRef = useRef(null);
  const previousRectRef = useRef(null);
  
  // Constants
  const STABILITY_THRESHOLD = 10; // Pixel difference threshold for stability
  const REQUIRED_STABLE_FRAMES = 15; // Number of stable frames required before capture
  
  // Default bean information
  const defaultBeanInfo = {
    name: `Unknown Coffee ${slotIndex}`,
    type: "arabica",
    roast: "medium",
    notes: "No flavor notes detected"
  };
  
  // Auto-start camera and detection on component mount
  useEffect(() => {
    startCamera();
    
    return () => {
      stopCamera();
    };
  }, []);
  
  // Camera control
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
        
        // Wait for video to be ready
        videoRef.current.onloadedmetadata = () => {
          setIsCameraOn(true);
          setMessage(`Place the ${currentSide.toUpperCase()} of the coffee bag in view. Detection running...`);
          
          // Start automatic boundary detection
          startBoundaryDetection();
        };
      }
    } catch (err) {
      console.error("Camera error:", err);
      setMessage(`Camera error: ${err.message}`);
    }
  };
  
  // Stop camera
  const stopCamera = () => {
    stopBoundaryDetection();
    
    // Clear stability timeout
    if (stableTimeoutRef.current) {
      clearTimeout(stableTimeoutRef.current);
      stableTimeoutRef.current = null;
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    
    setIsCameraOn(false);
    setShowBoundary(false);
    setBoundaryRect(null);
    setBoundaryStable(false);
    setBoundaryStableCount(0);
  };
  
  // Start boundary detection
  const startBoundaryDetection = () => {
    if (!videoRef.current || !boundaryCanvasRef.current) {
      setMessage("Video or canvas not ready");
      return;
    }
    
    // Reset state
    setBoundaryRect(null);
    setShowBoundary(false);
    setBoundaryStable(false);
    setBoundaryStableCount(0);
    previousRectRef.current = null;
    
    // Clear existing interval
    stopBoundaryDetection();
    
    // Run detection every 100ms
    boundaryDetectionRef.current = setInterval(() => {
      detectBoundaries();
    }, 100);
    
    setMessage(`Place the ${currentSide.toUpperCase()} of the coffee bag in view. Detection running...`);
  };
  
  // Stop boundary detection
  const stopBoundaryDetection = () => {
    if (boundaryDetectionRef.current) {
      clearInterval(boundaryDetectionRef.current);
      boundaryDetectionRef.current = null;
    }
  };
  
  // Detect object boundaries
  const detectBoundaries = () => {
    if (!videoRef.current || !canvasRef.current || !boundaryCanvasRef.current || !isCameraOn) {
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
      
      // Get image data
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const data = imageData.data;
      
      // Calculate boundaries of the object
      const rect = findObjectBoundaries(data, canvas.width, canvas.height);
      
      if (rect) {
        // Compare with previous rect to determine stability
        if (previousRectRef.current) {
          const prevRect = previousRectRef.current;
          
          // Calculate difference between current and previous rect
          const xDiff = Math.abs(rect.x - prevRect.x);
          const yDiff = Math.abs(rect.y - prevRect.y);
          const widthDiff = Math.abs(rect.width - prevRect.width);
          const heightDiff = Math.abs(rect.height - prevRect.height);
          
          // Check if the boundary is stable
          const isStable = (
            xDiff < STABILITY_THRESHOLD && 
            yDiff < STABILITY_THRESHOLD && 
            widthDiff < STABILITY_THRESHOLD && 
            heightDiff < STABILITY_THRESHOLD
          );
          
          if (isStable) {
            // Increment stable count
            setBoundaryStableCount(prevCount => {
              const newCount = prevCount + 1;
              
              // If we've reached the stability threshold
              if (newCount >= REQUIRED_STABLE_FRAMES && !boundaryStable) {
                setBoundaryStable(true);
                setMessage(`${currentSide.toUpperCase()} detected and stable! Capturing automatically...`);
                
                // Auto-capture after a short delay
                stableTimeoutRef.current = setTimeout(() => {
                  captureWithBoundary();
                }, 1000);
              }
              
              return newCount;
            });
          } else {
            // Reset stability if movement detected
            if (boundaryStableCount > 0) {
              setBoundaryStableCount(0);
              setBoundaryStable(false);
              
              // Clear auto-capture timeout
              if (stableTimeoutRef.current) {
                clearTimeout(stableTimeoutRef.current);
                stableTimeoutRef.current = null;
              }
              
              setMessage(`${currentSide.toUpperCase()} detected but moving. Hold steady...`);
            }
          }
        }
        
        // Update boundary rect and show it
        setBoundaryRect(rect);
        setShowBoundary(true);
        drawBoundaryRect(rect, boundaryStable);
        
        // Update previous rect
        previousRectRef.current = { ...rect };
        
        // Update message if not already set by stability logic
        if (!boundaryStable && boundaryStableCount === 0) {
          setMessage(`${currentSide.toUpperCase()} detected. Hold steady for auto-capture...`);
        }
      } else {
        // No boundaries found
        setBoundaryRect(null);
        setShowBoundary(false);
        setBoundaryStable(false);
        setBoundaryStableCount(0);
        previousRectRef.current = null;
        
        // Clear auto-capture timeout
        if (stableTimeoutRef.current) {
          clearTimeout(stableTimeoutRef.current);
          stableTimeoutRef.current = null;
        }
        
        // Clear the boundary canvas
        const boundaryCanvas = boundaryCanvasRef.current;
        const boundaryCtx = boundaryCanvas.getContext('2d');
        boundaryCanvas.width = canvas.width;
        boundaryCanvas.height = canvas.height;
        boundaryCtx.clearRect(0, 0, boundaryCanvas.width, boundaryCanvas.height);
        
        setMessage(`Place the ${currentSide.toUpperCase()} of the coffee bag in view. Detection running...`);
      }
    } catch (error) {
      console.error("Boundary detection error:", error);
    }
  };
  
  // Find object boundaries in the image data
  const findObjectBoundaries = (imageData, width, height) => {
    // Initialize boundary values
    let minX = width;
    let minY = height;
    let maxX = 0;
    let maxY = 0;
    let found = false;
    
    // Threshold for detecting significant pixel changes
    const threshold = 30;
    
    // Scan the image data to find boundaries
    for (let y = 0; y < height; y += 2) { // Skip rows for performance
      for (let x = 0; x < width; x += 2) { // Skip columns for performance
        const idx = (y * width + x) * 4;
        
        // Get pixel color components
        const r = imageData[idx];
        const g = imageData[idx + 1];
        const b = imageData[idx + 2];
        
        // Simple detection: calculating luminance
        const luminance = 0.299 * r + 0.587 * g + 0.114 * b;
        
        // Skip very bright pixels (likely background)
        if (luminance > 220) continue;
        
        // Calculate contrast with neighbors
        let contrast = 0;
        
        // Check right neighbor if not at right edge
        if (x < width - 2) {
          const rightIdx = (y * width + (x + 2)) * 4;
          const rightR = imageData[rightIdx];
          const rightG = imageData[rightIdx + 1];
          const rightB = imageData[rightIdx + 2];
          const rightLum = 0.299 * rightR + 0.587 * rightG + 0.114 * rightB;
          contrast = Math.max(contrast, Math.abs(luminance - rightLum));
        }
        
        // Check bottom neighbor if not at bottom edge
        if (y < height - 2) {
          const bottomIdx = ((y + 2) * width + x) * 4;
          const bottomR = imageData[bottomIdx];
          const bottomG = imageData[bottomIdx + 1];
          const bottomB = imageData[bottomIdx + 2];
          const bottomLum = 0.299 * bottomR + 0.587 * bottomG + 0.114 * bottomB;
          contrast = Math.max(contrast, Math.abs(luminance - bottomLum));
        }
        
        // If we found a significant contrast, update boundaries
        if (contrast > threshold) {
          minX = Math.min(minX, x);
          minY = Math.min(minY, y);
          maxX = Math.max(maxX, x);
          maxY = Math.max(maxY, y);
          found = true;
        }
      }
    }
    
    // Return null if no boundaries found
    if (!found) return null;
    
    // Add some padding to the boundaries
    const padding = 15;
    minX = Math.max(0, minX - padding);
    minY = Math.max(0, minY - padding);
    maxX = Math.min(width - 1, maxX + padding);
    maxY = Math.min(height - 1, maxY + padding);
    
    // Return the boundary rectangle
    return {
      x: minX,
      y: minY,
      width: maxX - minX,
      height: maxY - minY
    };
  };
  
  // Draw boundary rectangle on the boundary canvas
  const drawBoundaryRect = (rect, isStable) => {
    if (!boundaryCanvasRef.current) return;
    
    const canvas = boundaryCanvasRef.current;
    const ctx = canvas.getContext('2d');
    
    // Set canvas size to match video
    canvas.width = videoRef.current.videoWidth || 640;
    canvas.height = videoRef.current.videoHeight || 480;
    
    // Clear previous drawings
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw semi-transparent overlay outside the boundary
    ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
    
    // Top section
    ctx.fillRect(0, 0, canvas.width, rect.y);
    // Bottom section
    ctx.fillRect(0, rect.y + rect.height, canvas.width, canvas.height - (rect.y + rect.height));
    // Left section
    ctx.fillRect(0, rect.y, rect.x, rect.height);
    // Right section
    ctx.fillRect(rect.x + rect.width, rect.y, canvas.width - (rect.x + rect.width), rect.height);
    
    // Draw boundary rectangle - green if stable, yellow if not
    ctx.strokeStyle = isStable ? '#00FF00' : '#FFFF00';
    ctx.lineWidth = 3;
    ctx.strokeRect(rect.x, rect.y, rect.width, rect.height);
    
    // Draw corner guides
    const cornerSize = 15;
    ctx.beginPath();
    
    // Top-left corner
    ctx.moveTo(rect.x, rect.y + cornerSize);
    ctx.lineTo(rect.x, rect.y);
    ctx.lineTo(rect.x + cornerSize, rect.y);
    
    // Top-right corner
    ctx.moveTo(rect.x + rect.width - cornerSize, rect.y);
    ctx.lineTo(rect.x + rect.width, rect.y);
    ctx.lineTo(rect.x + rect.width, rect.y + cornerSize);
    
    // Bottom-right corner
    ctx.moveTo(rect.x + rect.width, rect.y + rect.height - cornerSize);
    ctx.lineTo(rect.x + rect.width, rect.y + rect.height);
    ctx.lineTo(rect.x + rect.width - cornerSize, rect.y + rect.height);
    
    // Bottom-left corner
    ctx.moveTo(rect.x + cornerSize, rect.y + rect.height);
    ctx.lineTo(rect.x, rect.y + rect.height);
    ctx.lineTo(rect.x, rect.y + rect.height - cornerSize);
    
    ctx.strokeStyle = isStable ? '#00FF00' : '#FFFF00';
    ctx.lineWidth = 3;
    ctx.stroke();
    
    // Add stability indicator
    const bgColor = isStable ? 'rgba(0, 128, 0, 0.7)' : 'rgba(255, 187, 0, 0.7)';
    ctx.fillStyle = bgColor;
    ctx.fillRect(rect.x, rect.y - 30, 180, 25);
    ctx.fillStyle = '#FFFFFF';
    ctx.font = '14px Arial';
    ctx.fillText(
      isStable ? 'STABLE - Capturing Soon' : `HOLD STEADY (${boundaryStableCount}/${REQUIRED_STABLE_FRAMES})`, 
      rect.x + 10, 
      rect.y - 12
    );
    
    // Draw side indicator
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(rect.x, rect.y + rect.height + 5, 100, 25);
    ctx.fillStyle = '#FFFFFF';
    ctx.font = '14px Arial';
    ctx.fillText(`${currentSide.toUpperCase()} SIDE`, rect.x + 10, rect.y + rect.height + 22);
  };
  
  // Simple capture with boundary cropping
  const captureWithBoundary = () => {
    if (!videoRef.current || !canvasRef.current || !boundaryRect) {
      setMessage("Cannot capture - video not ready or no boundaries detected");
      return;
    }
    
    // Clear stability timeout to prevent double captures
    if (stableTimeoutRef.current) {
      clearTimeout(stableTimeoutRef.current);
      stableTimeoutRef.current = null;
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
      
      // Set cropped canvas size to boundary dimensions
      croppedCanvas.width = boundaryRect.width;
      croppedCanvas.height = boundaryRect.height;
      
      // Draw only the boundary region to the cropped canvas
      croppedCtx.drawImage(
        canvas,
        boundaryRect.x, boundaryRect.y, boundaryRect.width, boundaryRect.height, // Source area
        0, 0, boundaryRect.width, boundaryRect.height // Destination area
      );
      
      // Get the cropped image data
      const imageData = croppedCanvas.toDataURL('image/jpeg', 0.95);
      
      // Save image based on current side
      if (currentSide === "front") {
        setFrontImage(imageData);
        setCurrentSide("back");
        setBoundaryRect(null);
        setShowBoundary(false);
        setBoundaryStable(false);
        setBoundaryStableCount(0);
        previousRectRef.current = null;
        
        // Start detection for back side
        setTimeout(() => {
          startBoundaryDetection();
        }, 500);
        
        setMessage("Front captured! Now scan the BACK of the bag.");
      } else {
        setBackImage(imageData);
        setMessage("Back captured! Processing...");
        stopBoundaryDetection();
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
  
  // Handle manual capture
  const handleManualCapture = () => {
    if (boundaryRect) {
      captureWithBoundary();
    } else {
      setMessage("No boundaries detected yet. Please position the coffee bag better.");
    }
  };
  
  // Handle cancel
  const handleCancel = () => {
    stopCamera();
    onCancel();
  };
  
  return (
    <div className="bg-white rounded p-4 mb-6">
      <h3 className="text-lg font-semibold mb-3">Scan Coffee Bag for Slot {slotIndex}</h3>
      
      {/* Status message */}
      <div className={`mb-4 p-2 rounded text-sm ${
        message.includes("detected and stable") ? "bg-green-100" :
        message.includes("Error") ? "bg-red-100" :
        message.includes("Processing") ? "bg-blue-100" :
        message.includes("detected but moving") ? "bg-yellow-100" :
        "bg-gray-100"
      }`}>
        {message}
      </div>
      
      {/* Video preview with boundary overlay */}
      <div className="mb-4 bg-black rounded relative" style={{ height: "300px" }}>
        {/* Video element */}
        <video
          ref={videoRef}
          style={{ width: "100%", height: "100%", objectFit: "contain" }}
          autoPlay
          playsInline
          muted
        />
        
        {/* Boundary canvas overlay */}
        <canvas
          ref={boundaryCanvasRef}
          className="absolute inset-0 w-full h-full"
          style={{ pointerEvents: "none" }}
        />
        
        {/* Hidden canvas for capturing */}
        <canvas ref={canvasRef} style={{ display: "none" }} />
        
        {/* Loading indicator */}
        {!isCameraOn && (
          <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-70">
            <div className="text-white flex flex-col items-center">
              <div className="w-10 h-10 border-t-2 border-b-2 border-white rounded-full animate-spin mb-2"></div>
              <p>Starting camera...</p>
            </div>
          </div>
        )}
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
        {isCameraOn && !processing && (
          <Button 
            text="Manual Capture" 
            onClick={handleManualCapture} 
            color="#386150"
            disabled={!boundaryRect}
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
      {isCameraOn && !processing && (
        <div className="mt-4 text-xs text-center text-gray-600">
          Position the coffee bag in frame. Boundaries will be detected automatically.
          {boundaryRect && !boundaryStable && (
            <p className="mt-1 font-medium">Hold steady for auto-capture, or press "Manual Capture" button.</p>
          )}
        </div>
      )}
    </div>
  );
};

export default BeanScanner;