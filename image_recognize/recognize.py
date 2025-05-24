from ultralytics import YOLO

def recognize_image(image_path):
    """
    Recognize the image using the image recognition model.
    :param image_path: Path to the image file.
    :return: Recognition result.
    """
    model = YOLO("image_recognize/yolo_model_m/weights/best.pt")  # Load the trained model

    # Perform recognition
    result = model.predict(image_path)

    model_names = result[0].names
    top5_indices = result[0].probs.top5
    top5_confidence = result[0].probs.top5conf.tolist()
    top5_names = [model_names[idx] for idx in top5_indices]

    return top5_names, top5_confidence


if __name__ == "__main__":
    # Example usage
    image_path = "image_recognize/test/test1.png"
    result = recognize_image(image_path)
    print(result)


