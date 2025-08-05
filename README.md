# DMA VTT - Virtual Tabletop System

A modular Virtual Tabletop System (VTT) for roleplaying games in the browser.

## Project Overview

DMA VTT is a web-based virtual tabletop system that allows Game Masters (GMs) and players to participate in roleplaying sessions. The system features user authentication, scene management, real-time synchronization, and interactive canvas elements.

## Backend Structure

The backend is built with Python and Flask, using PostgreSQL for data storage and WebSockets for real-time communication.

### Key Components

- **Authentication System**: Secure login with Argon2 password hashing and JWT tokens
- **Database Models**: SQLAlchemy models for users, scenes, layers, tokens, etc.
- **REST API**: Endpoints for resource management
- **WebSocket Handlers**: Real-time synchronization of canvas changes

## Frontend Structure

The frontend is built with Angular, using TypeScript and Angular Material for UI components. Below is the recommended structure for the Angular project.

### Project Setup

```bash
# Install Angular CLI
npm install -g @angular/cli

# Create a new Angular project
ng new dma-vtt-client --routing --style=scss

# Navigate to the project directory
cd dma-vtt-client

# Install dependencies
npm install @angular/material @angular/cdk @angular/flex-layout
npm install konva ng2-konva
npm install socket.io-client
npm install jwt-decode
npm install squoosh
```

### Project Structure

```
src/
├── app/
│   ├── core/                  # Core functionality
│   │   ├── auth/              # Authentication services
│   │   ├── models/            # TypeScript interfaces
│   │   ├── services/          # API services
│   │   └── websocket/         # WebSocket service
│   ├── shared/                # Shared components
│   │   ├── components/        # Reusable UI components
│   │   ├── directives/        # Custom directives
│   │   └── pipes/             # Custom pipes
│   ├── features/              # Feature modules
│   │   ├── auth/              # Authentication feature
│   │   │   ├── login/         # Login component
│   │   │   └── register/      # Registration component (GM only)
│   │   ├── scenes/            # Scene management
│   │   │   ├── scene-list/    # Scene list component (GM only)
│   │   │   └── scene-view/    # Scene viewer component
│   │   ├── canvas/            # Canvas feature
│   │   │   ├── canvas/        # Main canvas component
│   │   │   ├── layer-panel/   # Layer management panel (GM only)
│   │   │   ├── tools-panel/   # Drawing tools panel
│   │   │   └── token-panel/   # Token management panel
│   │   ├── dice/              # Dice rolling feature
│   │   │   ├── dice-roller/   # Dice roller component
│   │   │   └── dice-log/      # Dice roll history component
│   │   └── notes/             # Notes feature
│   │       ├── note-editor/   # Note editor component
│   │       └── point-tracker/ # Point tracker component
│   ├── app-routing.module.ts  # Application routing
│   ├── app.component.ts       # Root component
│   └── app.module.ts          # Root module
└── assets/                    # Static assets
    ├── images/                # Image assets
    └── styles/                # Global styles
```

### Key Components

#### Authentication

- **Login Component**: User login form
- **Auth Service**: Handles authentication API calls and token storage
- **Auth Guard**: Protects routes based on authentication status and role

#### Scene Management

- **Scene List Component**: Displays a list of scenes with thumbnails (GM only)
- **Scene View Component**: Displays the active scene with layers and interactive elements

#### Canvas

- **Canvas Component**: Main drawing area using Konva.js
- **Layer Panel Component**: Manages layers and their visibility (GM only)
- **Tools Panel Component**: Drawing tools for the player layer
- **Token Panel Component**: Token library and management (GM only)

#### Dice Rolling

- **Dice Roller Component**: Interface for rolling dice with 3D animations
- **Dice Log Component**: History of dice rolls

#### Notes

- **Note Editor Component**: Markdown editor for player notes
- **Point Tracker Component**: Resource tracker with visual representation

### WebSocket Integration

The WebSocket service will handle real-time communication with the server:

```typescript
// src/app/core/websocket/websocket.service.ts
import { Injectable } from '@angular/core';
import { Socket, io } from 'socket.io-client';
import { Observable } from 'rxjs';
import { AuthService } from '../auth/auth.service';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class WebSocketService {
  private socket: Socket;

  constructor(private authService: AuthService) {
    this.socket = io(environment.apiUrl, {
      auth: {
        token: this.authService.getToken()
      }
    });
  }

  // Listen to events
  public on<T>(event: string): Observable<T> {
    return new Observable<T>(observer => {
      this.socket.on(event, (data: T) => {
        observer.next(data);
      });
    });
  }

  // Emit events
  public emit(event: string, data: any): void {
    this.socket.emit(event, data);
  }

  // Disconnect
  public disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
    }
  }
}
```

### Canvas Implementation

The canvas will be implemented using Konva.js:

```typescript
// src/app/features/canvas/canvas/canvas.component.ts
import { Component, OnInit, OnDestroy } from '@angular/core';
import { WebSocketService } from '../../../core/websocket/websocket.service';
import { SceneService } from '../../../core/services/scene.service';
import { AuthService } from '../../../core/auth/auth.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-canvas',
  templateUrl: './canvas.component.html',
  styleUrls: ['./canvas.component.scss']
})
export class CanvasComponent implements OnInit, OnDestroy {
  private subscriptions: Subscription[] = [];
  public layers: any[] = [];
  public activeLayer: any;
  public isAdmin: boolean;

  constructor(
    private webSocketService: WebSocketService,
    private sceneService: SceneService,
    private authService: AuthService
  ) {
    this.isAdmin = this.authService.isAdmin();
  }

  ngOnInit(): void {
    // Load active scene
    this.loadActiveScene();

    // Subscribe to WebSocket events
    this.subscribeToEvents();
  }

  ngOnDestroy(): void {
    // Unsubscribe from all subscriptions
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  private loadActiveScene(): void {
    this.sceneService.getActiveScene().subscribe(scene => {
      this.layers = scene.layers;
      // Initialize Konva stage and layers
      this.initializeCanvas();
    });
  }

  private subscribeToEvents(): void {
    // Token movement
    this.subscriptions.push(
      this.webSocketService.on<any>('token_moved').subscribe(data => {
        this.updateTokenPosition(data);
      })
    );

    // Drawing created
    this.subscriptions.push(
      this.webSocketService.on<any>('drawing_created').subscribe(data => {
        this.addDrawing(data);
      })
    );

    // Text created
    this.subscriptions.push(
      this.webSocketService.on<any>('text_created').subscribe(data => {
        this.addText(data);
      })
    );

    // Scene activated
    this.subscriptions.push(
      this.webSocketService.on<any>('scene_activated').subscribe(data => {
        this.loadActiveScene();
      })
    );
  }

  private initializeCanvas(): void {
    // Initialize Konva stage and layers
    // This would be implemented using ng2-konva
  }

  private updateTokenPosition(data: any): void {
    // Update token position in the canvas
  }

  private addDrawing(data: any): void {
    // Add new drawing to the canvas
  }

  private addText(data: any): void {
    // Add new text to the canvas
  }

  // Methods for user interactions (token movement, drawing, etc.)
}
```

### WebP Image Conversion

For WebP image conversion, we'll use the Squoosh library:

```typescript
// src/app/core/services/image.service.ts
import { Injectable } from '@angular/core';
import { encode } from 'squoosh';

@Injectable({
  providedIn: 'root'
})
export class ImageService {
  constructor() {}

  async convertToWebP(file: File): Promise<File> {
    // Read the file as an ArrayBuffer
    const arrayBuffer = await file.arrayBuffer();
    
    // Encode to WebP
    const result = await encode(new Uint8Array(arrayBuffer), {
      webp: {
        quality: 80
      }
    });
    
    // Create a new File object
    const webpFile = new File([result.webp.binary], 
      file.name.replace(/\.[^/.]+$/, '.webp'), 
      { type: 'image/webp' }
    );
    
    return webpFile;
  }
}
```

## Setup Instructions

### Backend Setup

1. Install dependencies:
   ```bash
   pip install -e .
   ```

2. Set environment variables:
   ```bash
   export SECRET_KEY=your_secret_key
   export DATABASE_URL=postgresql://username:password@localhost/dma_vtt
   export ADMIN_USERNAME=admin
   export ADMIN_PASSWORD=secure_password
   export UPLOAD_FOLDER=uploads
   ```

3. Create the PostgreSQL database:
   ```bash
   createdb dma_vtt
   ```

4. Run the server:
   ```bash
   vtt-server
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure the environment:
   Edit `src/environments/environment.ts` to point to your backend API.

4. Run the development server:
   ```bash
   ng serve
   ```

5. Access the application at `http://localhost:4200`

## License

[MIT License](LICENSE)