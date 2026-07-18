/**
 * react-global.d.ts
 *
 * Makes the `React` namespace available globally so that files can reference
 * `React.ElementType`, `React.FC`, `React.ReactNode`, etc. without an explicit
 * `import React from 'react'` in every file.
 *
 * Background: with `"jsx": "react-jsx"` (automatic JSX runtime), TypeScript
 * no longer injects `import React` for JSX, so `React.*` type annotations in
 * module files fail unless React is brought into scope.  This shim declares a
 * matching global namespace so legacy annotations continue to compile.
 */

import type {
  ElementType,
  FC,
  ReactNode,
  ReactElement,
  ReactChild,
  FormEvent,
  KeyboardEvent,
  MouseEvent,
  ChangeEvent,
  FocusEvent,
  DragEvent,
  TouchEvent,
  WheelEvent,
  CSSProperties,
  PropsWithChildren,
  Dispatch,
  SetStateAction,
  RefObject,
  MutableRefObject,
  Ref,
  HTMLAttributes,
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  TextareaHTMLAttributes,
  SelectHTMLAttributes,
  AnchorHTMLAttributes,
  ImgHTMLAttributes,
  SVGAttributes,
  AriaAttributes,
  Context,
  Provider,
  Consumer,
  Component,
  ComponentType,
  ComponentProps,
  ComponentPropsWithRef,
  ComponentPropsWithoutRef,
  EventHandler,
  SyntheticEvent,
  ClipboardEvent,
  AnimationEvent,
  TransitionEvent,
  ReactPortal,
  ReactFragment,
} from 'react';

declare global {
  namespace React {
    export type {
      ElementType,
      FC,
      ReactNode,
      ReactElement,
      ReactChild,
      FormEvent,
      KeyboardEvent,
      MouseEvent,
      ChangeEvent,
      FocusEvent,
      DragEvent,
      TouchEvent,
      WheelEvent,
      CSSProperties,
      PropsWithChildren,
      Dispatch,
      SetStateAction,
      RefObject,
      MutableRefObject,
      Ref,
      HTMLAttributes,
      ButtonHTMLAttributes,
      InputHTMLAttributes,
      TextareaHTMLAttributes,
      SelectHTMLAttributes,
      AnchorHTMLAttributes,
      ImgHTMLAttributes,
      SVGAttributes,
      AriaAttributes,
      Context,
      Provider,
      Consumer,
      Component,
      ComponentType,
      ComponentProps,
      ComponentPropsWithRef,
      ComponentPropsWithoutRef,
      EventHandler,
      SyntheticEvent,
      ClipboardEvent,
      AnimationEvent,
      TransitionEvent,
      ReactPortal,
      ReactFragment,
    };
  }
}
