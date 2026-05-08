import CoreGraphics
import Foundation
import ImageIO
import Vision

struct OCRResult: Codable {
    let path: String
    let status: String
    let text: String
    let confidence: Float
    let error: String?
}

func loadCGImage(path: String) throws -> CGImage {
    let url = URL(fileURLWithPath: path)
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil) else {
        throw NSError(domain: "VisionOCR", code: 1, userInfo: [NSLocalizedDescriptionKey: "Cannot create image source"])
    }
    guard let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
        throw NSError(domain: "VisionOCR", code: 2, userInfo: [NSLocalizedDescriptionKey: "Cannot load CGImage"])
    }
    return image
}

func recognize(path: String, recognitionLevel: VNRequestTextRecognitionLevel) -> OCRResult {
    do {
        let image = try loadCGImage(path: path)
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = recognitionLevel
        request.usesLanguageCorrection = true
        request.recognitionLanguages = ["en-US"]

        let handler = VNImageRequestHandler(cgImage: image, options: [:])
        try handler.perform([request])

        let observations = request.results ?? []
        var lines: [String] = []
        var confidences: [Float] = []
        for observation in observations {
            guard let candidate = observation.topCandidates(1).first else { continue }
            lines.append(candidate.string)
            confidences.append(candidate.confidence)
        }
        let average = confidences.isEmpty ? 0 : confidences.reduce(0, +) / Float(confidences.count)
        return OCRResult(path: path, status: "ok", text: lines.joined(separator: "\n"), confidence: average, error: nil)
    } catch {
        return OCRResult(path: path, status: "error", text: "", confidence: 0, error: String(describing: error))
    }
}

let args = Array(CommandLine.arguments.dropFirst())
let fast = args.contains("--fast")
let imagePaths = args.filter { !$0.hasPrefix("--") }
let encoder = JSONEncoder()
encoder.outputFormatting = [.withoutEscapingSlashes]

for imagePath in imagePaths {
    let result = recognize(path: imagePath, recognitionLevel: fast ? .fast : .accurate)
    if let data = try? encoder.encode(result), let line = String(data: data, encoding: .utf8) {
        print(line)
        fflush(stdout)
    }
}

