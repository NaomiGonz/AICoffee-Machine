import React, { useState, useRef, useEffect } from "react";
import Button from "../components/Button.jsx";

// Debug logging helper
const logDebug = (message, data = null) => {
  const timestamp = new Date().toLocaleTimeString();
  const logPrefix = `[${timestamp}] 🔍 BeanScanner:`;
  
  if (data) {
    console.log(logPrefix, message, data);
  } else {
    console.log(logPrefix, message);
  }
};

const BeanScanner = ({ onScanComplete, slotIndex, onCancel }) => {
  const [scanning, setScanning] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState("Starting camera...");
  const [frontImage, setFrontImage] = useState(null);
  const [backImage, setBackImage] = useState(null);
  const [currentSide, setCurrentSide] = useState("front");
  const [detectionStatus, setDetectionStatus] = useState(null);
  const [apiError, setApiError] = useState(null);
  
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  
  // Default bean information to use if detection fails
  const defaultBeanInfo = {
    name: `Unknown Coffee ${slotIndex}`,
    type: "arabica",
    roast: "medium",
    notes: "No flavor notes detected"
  };
  
  // Component lifecycle logging
  useEffect(() => {
    logDebug(`Component mounted for slot ${slotIndex}`);
    startCamera();
    
    return () => {
      logDebug(`Component unmounting for slot ${slotIndex}`);
      stopCamera();
    };
  }, []);
  
  // Start the camera feed
  const startCamera = async () => {
    logDebug("Starting camera...");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          facingMode: "environment",
          width: { ideal: 1280 },
          height: { ideal: 720 }
        } 
      });
      
      logDebug("Camera access granted");
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        streamRef.current = stream;
        setScanning(true);
        setCurrentSide("front");
        setFeedbackMessage("Center the FRONT of the coffee bag within the frame and capture.");
      }
    } catch (err) {
      const errorMsg = `Camera error: ${err.message}. Please ensure camera permissions are granted.`;
      logDebug("Camera error", err);
      console.error("Camera access error:", err);
      setFeedbackMessage(errorMsg);
    }
  };
  
  // Stop the camera feed
  const stopCamera = () => {
    if (streamRef.current) {
      logDebug("Stopping camera stream");
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
      setScanning(false);
    }
  };
  
  // Capture an image from the video feed
  const captureImage = () => {
    if (!videoRef.current || !canvasRef.current) {
      logDebug("Video or canvas refs not available");
      return;
    }
    
    logDebug(`Capturing ${currentSide} image`);
    
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const context = canvas.getContext("2d");
    
    // Set canvas dimensions to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    // Draw the current video frame to the canvas
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Get the image data as base64
    const imageData = canvas.toDataURL("image/jpeg");
    logDebug(`${currentSide} image captured, size: ${Math.round(imageData.length / 1024)} KB`);
    
    if (currentSide === "front") {
      setFrontImage(imageData);
      setCurrentSide("back");
      setFeedbackMessage("Front captured! Now center the BACK of the bag within the frame and capture.");
    } else {
      setBackImage(imageData);
      setFeedbackMessage("Back captured! Processing images...");
      setTimeout(() => processImages(frontImage, imageData), 500);
    }
  };
  
  // Process the captured images using GPT-4 Vision API
  const processImages = async (frontImage, backImage) => {
    if (!frontImage || !backImage) {
      const errorMsg = "Missing images. Please try again.";
      logDebug(errorMsg);
      setFeedbackMessage(errorMsg);
      return;
    }
    
    setProcessing(true);
    setApiError(null);
    
    logDebug("Starting image processing");
    
    try {
      // Prepare the data for the API
      logDebug("Preparing images for API submission");
      const frontImageBase64 = frontImage.split(',')[1]; // Remove the data:image/jpeg;base64, prefix
      const backImageBase64 = backImage.split(',')[1];
      
      const apiRequestData = {
        front_image: frontImageBase64,
        back_image: backImageBase64,
        slot_index: slotIndex
      };
      
      logDebug("Sending request to backend API");
      
      const response = await fetch("http://localhost:8000/api/process-coffee-bag", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(apiRequestData)
      });
      
      logDebug(`API response status: ${response.status}`);
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API error: ${response.status} - ${response.statusText}. Details: ${errorText}`);
      }
      
      const data = await response.json();
      logDebug("API response data", data);
      
      // Check if the API was able to identify a coffee bag
      if (data.detection_status === "failed" || !data.name) {
        setDetectionStatus("failed");
        const errorMsg = "Could not clearly identify a coffee bag in the images. Using default values.";
        logDebug(errorMsg);
        setFeedbackMessage(errorMsg);
        
        // If any fields are empty or missing, use default values
        const beanInfo = {
          name: defaultBeanInfo.name,
          type: defaultBeanInfo.type,
          roast: defaultBeanInfo.roast,
          notes: defaultBeanInfo.notes
        };
        
        logDebug("Using default bean info", beanInfo);
        onScanComplete(slotIndex, beanInfo);
      } else {
        setDetectionStatus("success");
        
        // Map the response to the format expected by the parent component
        const beanInfo = {
          name: data.name || defaultBeanInfo.name,
          type: data.type || defaultBeanInfo.type,
          roast: data.roast ? data.roast.toLowerCase() : defaultBeanInfo.roast,
          notes: data.notes || defaultBeanInfo.notes
        };
        
        logDebug("Scan completed successfully", beanInfo);
        setFeedbackMessage(`Successfully identified: ${beanInfo.name}`);
        
        // Pass the bean information back to the parent component
        onScanComplete(slotIndex, beanInfo);
      }
      
    } catch (error) {
      logDebug("Error processing images", error);
      console.error("Error processing images:", error);
      
      const errorMsg = `Error processing images: ${error.message}. Using default values.`;
      setFeedbackMessage(errorMsg);
      setDetectionStatus("error");
      setApiError(error.message);
      
      // Use default values if there's an error
      logDebug("Using default bean info due to error", defaultBeanInfo);
      onScanComplete(slotIndex, defaultBeanInfo);
      
      // Close scanner after error
      setTimeout(() => {
        if (onCancel) onCancel();
      }, 3000);
    } finally {
      setProcessing(false);
    }
  };
  
  return (
    <div className="bg-white rounded p-4 mb-6">
      <h3 className="text-lg font-semibold mb-3">Scan Coffee Bag for Slot {slotIndex}</h3>
      
      {/* Feedback area */}
      {feedbackMessage && (
        <div className={`mb-4 p-2 rounded text-sm ${
          feedbackMessage.includes("Warning") ? "bg-yellow-100" : 
          detectionStatus === "failed" ? "bg-red-100" :
          detectionStatus === "success" ? "bg-green-100" :
          detectionStatus === "error" ? "bg-red-100" :
          "bg-gray-100"
        }`}>
          {feedbackMessage}
        </div>
      )}
      
      {/* API Error display */}
      {apiError && (
        <div className="mb-4 p-2 bg-red-100 rounded text-sm border border-red-300">
          <p className="font-semibold">API Error:</p>
          <p className="text-xs">{apiError}</p>
        </div>
      )}
      
      {/* Camera feed with visual guides for vertical bags */}
      {scanning && (
        <div className="relative mb-4">
          <video 
            ref={videoRef} 
            className="w-full h-80 object-cover border border-gray-300 rounded" 
            autoPlay 
            playsInline
          />
          <canvas ref={canvasRef} className="hidden" />
          
          {/* Visual targeting guides - taller rectangle for vertical bags */}
          <div className="absolute inset-0 pointer-events-none">
            {/* Center rectangle guide - taller and narrower for vertical bags */}
            <div className="absolute border-2 border-dashed border-green-600 rounded-lg"
              style={{
                top: '5%',
                left: '25%',
                right: '25%',
                bottom: '5%',
                boxShadow: '0 0 0 2000px rgba(0, 0, 0, 0.15)'
              }}>
              {/* Corner markers */}
              <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-green-600"></div>
              <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-green-600"></div>
              <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-green-600"></div>
              <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-green-600"></div>
            </div>
            
            {/* Side indicator (Front/Back) */}
            <div className="absolute top-2 left-1/2 transform -translate-x-1/2 bg-green-600 text-white px-3 py-1 rounded-full text-sm font-bold">
              {currentSide.toUpperCase()} SIDE
            </div>
            
            {/* Instructions */}
            <div className="absolute bottom-2 left-1/2 transform -translate-x-1/2 bg-black bg-opacity-70 text-white px-4 py-2 rounded-lg text-xs max-w-xs text-center">
              Center the {currentSide} of the coffee bag vertically within the green outline
            </div>
          </div>
        </div>
      )}
      
      {/* Captured images preview */}
      <div className="flex gap-2 mb-4">
        <div className="w-1/2">
          <p className="text-xs text-gray-600 mb-1">Front</p>
          {frontImage ? (
            <img 
              src={frontImage} 
              alt="Front of coffee bag" 
              className="w-full h-36 object-cover border rounded"
            />
          ) : (
            <div className="w-full h-36 bg-gray-200 border rounded flex items-center justify-center text-gray-500 text-sm">
              Not captured
            </div>
          )}
        </div>
        <div className="w-1/2">
          <p className="text-xs text-gray-600 mb-1">Back</p>
          {backImage ? (
            <img 
              src={backImage} 
              alt="Back of coffee bag" 
              className="w-full h-36 object-cover border rounded"
            />
          ) : (
            <div className="w-full h-36 bg-gray-200 border rounded flex items-center justify-center text-gray-500 text-sm">
              Not captured
            </div>
          )}
        </div>
      </div>
      
      {/* Debug info section */}
      <div className="mb-4 p-2 bg-gray-100 rounded text-xs">
        <p><strong>Debug Info:</strong> {processing ? "Processing..." : "Ready"}</p>
        <p>Endpoint: /api/process-coffee-bag</p>
        <p>Status: {detectionStatus || "Waiting for image capture"}</p>
      </div>
      
      {/* Control buttons */}
      <div className="flex gap-2 justify-center">
        {scanning ? (
          <>
            {!processing && (
              <Button 
                text={`Capture ${currentSide.toUpperCase()}`} 
                onClick={captureImage} 
                color="#386150"
              />
            )}
            <Button 
              text={processing ? "Processing..." : "Cancel"} 
              onClick={onCancel} 
              color="#DD6B55"
              disabled={processing}
            />
          </>
        ) : (
          <Button 
            text="Start Scanning" 
            onClick={startCamera} 
            color="#386150"
          />
        )}
      </div>
    </div>
  );
};

export default BeanScanner;