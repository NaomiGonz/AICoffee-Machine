import React, { useState } from 'react';

// Define the machine code type
interface MachineCode {
  commands: string[];
}

interface MachineCodeVisualizationProps {
  machineCode: MachineCode;
}

// Define step type
interface BrewStep {
  command: string;
  desc: string;
}

// Define phase type
interface BrewPhase {
  id: string;
  title: string;
  icon: string;
  steps: BrewStep[];
  color: string;
}

const MachineCodeVisualization: React.FC<MachineCodeVisualizationProps> = ({ machineCode }) => {
  const [showDetails, setShowDetails] = useState(false);
  
  if (!machineCode || !machineCode.commands) {
    return <p className="text-gray-500 italic">No machine code available</p>;
  }

  // Parse the machine code into process phases
  const parseProcessPhases = (commands: string[]) => {
    const phases: BrewPhase[] = [
      { id: 'grinding', title: 'Grinding', icon: '⚙️', steps: [], color: 'bg-amber-100' },
      { id: 'dispensing', title: 'Bean Dispensing', icon: '☕', steps: [], color: 'bg-amber-200' },
      { id: 'brewing', title: 'Brewing', icon: '🔄', steps: [], color: 'bg-amber-300' },
      { id: 'extraction', title: 'Extraction', icon: '💧', steps: [], color: 'bg-amber-400' }
    ];

    // Categorize commands into phases
    let currentPhase = 0;
    
    commands.forEach((cmd, index) => {
      if (cmd.startsWith('G-')) {
        const rpm = parseInt(cmd.split('-')[1]);
        if (rpm > 0) {
          phases[0].steps.push({ 
            command: cmd, 
            desc: `Grinder: ${rpm} RPM` 
          });
        } else {
          phases[0].steps.push({ 
            command: cmd, 
            desc: 'Grinder Off' 
          });
          currentPhase = 1; // Move to next phase
        }
      } 
      else if (cmd.startsWith('S-')) {
        const parts = cmd.split('-');
        const hopper = parts[1];
        const time = parseFloat(parts[2]);
        
        phases[1].steps.push({ 
          command: cmd, 
          desc: `Hopper ${hopper}: ${time}s` 
        });
      }
      else if (cmd.startsWith('R-')) {
        const rpm = parseInt(cmd.split('-')[1]);
        if (rpm > 0) {
          currentPhase = 2; // Move to brewing phase
          phases[2].steps.push({ 
            command: cmd, 
            desc: `Drum: ${rpm} RPM` 
          });
        } else {
          phases[2].steps.push({ 
            command: cmd, 
            desc: 'Drum Off' 
          });
        }
      }
      else if (cmd.startsWith('H-')) {
        const power = parseInt(cmd.split('-')[1]);
        let temp;
        if (power >= 90) temp = "94-96°C";
        else if (power >= 70) temp = "91-93°C";
        else temp = "88-90°C";
        
        phases[2].steps.push({ 
          command: cmd, 
          desc: `Heat: ${temp}` 
        });
      }
      else if (cmd.startsWith('P-')) {
        const parts = cmd.split('-');
        const volume = parseInt(parts[1]);
        const rate = parseFloat(parts[2]);
        
        currentPhase = 3; // Move to extraction phase
        
        let cupSize;
        if (volume <= 100) cupSize = "Small (3oz)";
        else if (volume <= 220) cupSize = "Medium (7oz)";
        else cupSize = "Large (10oz)";
        
        phases[3].steps.push({ 
          command: cmd, 
          desc: `Water: ${volume}mL @ ${rate}mL/s (${cupSize})` 
        });
      }
      else if (cmd.startsWith('D-')) {
        // Add delay to current phase
        const delay = parseInt(cmd.split('-')[1]);
        const seconds = (delay / 1000).toFixed(1);
        
        phases[currentPhase].steps.push({ 
          command: cmd, 
          desc: `Wait: ${seconds}s` 
        });
      }
    });
    
    // Calculate total brew time properly by summing all execution times
    let totalTime = 0;
    
    // Sum all D- commands (delays)
    commands.forEach(cmd => {
      if (cmd.startsWith('D-')) {
        totalTime += parseInt(cmd.split('-')[1]) / 1000;
      }
    });
    
    // Add S- command times (servo operation times)
    commands.forEach(cmd => {
      if (cmd.startsWith('S-')) {
        // Only count if not already covered by a delay
        const servoTime = parseFloat(cmd.split('-')[2]);
        // Check if there's a corresponding delay for this servo operation
        const hasMatchingDelay = commands.some(delayCmd => {
          if (delayCmd.startsWith('D-')) {
            const delayMs = parseInt(delayCmd.split('-')[1]);
            const delaySeconds = delayMs / 1000;
            // If a delay matches the servo time (with some margin), assume it accounts for this
            return Math.abs(delaySeconds - servoTime) < 0.5;
          }
          return false;
        });
        
        if (!hasMatchingDelay) {
          totalTime += servoTime;
        }
      }
    });
    
    // Add water pumping time if not covered by a delay
    const pumpCmd = commands.find(cmd => cmd.startsWith('P-'));
    if (pumpCmd) {
      const parts = pumpCmd.split('-');
      const pumpTime = parseInt(parts[1]) / parseFloat(parts[2]);
      
      // Check if there's a delay that covers this pump operation
      const hasMatchingDelay = commands.some(delayCmd => {
        if (delayCmd.startsWith('D-')) {
          const delayMs = parseInt(delayCmd.split('-')[1]);
          const delaySeconds = delayMs / 1000;
          // If any delay is longer than pump time, assume it accounts for this
          return delaySeconds >= pumpTime;
        }
        return false;
      });
      
      if (!hasMatchingDelay) {
        totalTime += pumpTime;
      }
    }
    
    // Add summary metrics
    const metrics = {
      totalTime: totalTime.toFixed(1)
    };
    
    return { phases, metrics };
  };

  const { phases, metrics } = parseProcessPhases(machineCode.commands);
  
  // Get water temperature
  const getTemperature = () => {
    const heaterCmd = machineCode.commands.find(cmd => cmd.startsWith('H-'));
    if (!heaterCmd) return "92 PWM";
    
    const power = parseInt(heaterCmd.split('-')[1]);
    if (power >= 90) return "95 PWM";
    else if (power >= 70) return "92 PWM";
    else return "89 PWM";
  };
  
  return (
    <div className="bg-white p-4 rounded-lg shadow-md">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-md md:text-lg font-medium">Brewing Process</h3>
        <button 
          onClick={() => setShowDetails(!showDetails)}
          className="text-xs px-3 py-1 bg-gray-100 rounded-md hover:bg-gray-200"
        >
          {showDetails ? "Hide Details" : "Show Details"}
        </button>
      </div>
      
      {/* Quick summary stats */}
      <div className="grid grid-cols-2 gap-2 mb-4 text-center">
        <div className="p-2 bg-gray-50 rounded-md">
          <div className="text-xs text-gray-500">Brew Time</div>
          <div className="font-bold">{metrics.totalTime}s</div>
        </div>
        <div className="p-2 bg-gray-50 rounded-md">
          <div className="text-xs text-gray-500">Temperature</div>
          <div className="font-bold">{getTemperature()}</div>
        </div>
      </div>
      
      {/* Process flow visualization */}
      <div className="relative mb-6">
        <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-300 z-0"></div>
        
        {phases.map((phase, phaseIndex) => (
          <div key={phase.id} className="relative z-10 mb-3">
            <div className="flex items-center">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${phase.color} text-lg`}>
                {phase.icon}
              </div>
              <div className="ml-3 font-medium">{phase.title}</div>
            </div>
            
            {showDetails && phase.steps.length > 0 && (
              <div className="ml-10 mt-2 space-y-2">
                {phase.steps.map((step, stepIndex) => (
                  <div key={`${phase.id}-${stepIndex}`} className="flex text-sm">
                    <div className="text-gray-600 w-32">{step.desc}</div>
                    <div className="text-xs text-gray-400 font-mono">{step.command}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      
      {/* Technical reference */}
      {showDetails && (
        <div className="text-xs text-gray-600 mt-2 p-2 bg-gray-50 rounded-md">
          <p className="font-bold mb-1">Command Reference:</p>
          <ul className="grid grid-cols-2 gap-x-4 gap-y-1">
            <li>G-XXXX: Grinder RPM</li>
            <li>S-X-YY: Bean dispenser</li>
            <li>R-XXXX: Drum rotation</li>
            <li>H-XX: Heater power</li>
            <li>P-XXX-YY: Water pump</li>
            <li>D-XXXX: Delay (ms)</li>
          </ul>
        </div>
      )}
    </div>
  );
};

export default MachineCodeVisualization;