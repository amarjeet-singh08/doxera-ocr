declare module "liquid-gl" {
  export interface LiquidGLOptions {
    target: HTMLElement | string;
    snapshot?: string;
    engine?: "auto" | "webgpu" | "webgl2" | "webgl";
    refraction?: number;
    bevel?: number;
    aberration?: number;
    interaction?: "fluid" | "none";
    interactionStrength?: number;
    interactionRadius?: number;
    interactionViscosity?: number;
    zIndex?: number;
    shadow?: boolean;
    tilt?: boolean;
    draggable?: boolean;
  }

  export interface LiquidLensInstance {
    destroy: () => void;
    setDraggable: (draggable: boolean) => void;
  }

  export function liquidGL(options: LiquidGLOptions): LiquidLensInstance;
  export default liquidGL;
}
