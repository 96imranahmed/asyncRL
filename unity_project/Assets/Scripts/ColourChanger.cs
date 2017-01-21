using UnityEngine;
using System.Collections;

public class ColourChanger : MonoBehaviour {

    public Color colour;

	// Use this for initialization
	void Start () {
        gameObject.GetComponent<Renderer>().material.color = colour;
	}
}
